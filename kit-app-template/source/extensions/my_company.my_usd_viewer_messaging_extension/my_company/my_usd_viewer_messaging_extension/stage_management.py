# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pxr import Gf, UsdGeom, Usd

import colorsys
import asyncio
import math
import time

import carb
import carb.dictionary
import carb.events
import carb.settings
import carb.tokens
import omni.client.utils
import omni.ext
import omni.usd
import omni.kit.app
import omni.kit.commands
import omni.kit.viewport.utility
import omni.kit.livestream.messaging as messaging

from carb.eventdispatcher import get_eventdispatcher
from omni.kit.viewport.utility import get_active_viewport_camera_string


class StageManager:
    """This class manages the stage and its related events."""
    def __init__(self):
        # Internal messaging state
        self._is_external_update: bool = False
        self._camera_attrs = {}
        self._orbit_state = None
        self._subscriptions = []
        self._sample_telemetry_task = None

        # -- register outgoing events/messages
        outgoing = [
            # notify when user selects something in the viewport.
            "stageSelectionChanged",
            # response to request for children of a prim
            "getChildrenResponse",
            # response to request for primitive being pickable.
            "makePrimsPickableResponse",
            # response to the request to reset camera attributes
            "resetStageResponse",
            # response after applying live gasifier telemetry
            "gasifierTelemetryUpdated",
        ]

        for o in outgoing:
            messaging.register_event_type_to_send(o)
            omni.kit.app.register_event_alias(
                carb.events.type_from_string(o),
                o,
            )

        # -- register incoming events/messages
        incoming = {
            # request to get children of a prim
            'getChildrenRequest': self._on_get_children,
            # request to select a prim
            'selectPrimsRequest': self._on_select_prims,
            # request to make primitives pickable
            'makePrimsPickable': self._on_make_pickable,
            # request to reset stage
            'resetStage': self._on_reset_camera,
            # request to frame selection
            'frameSelection': self._on_frame_selection,
            # animation playback controls
            'playAnimation': self._on_play_animation,
            'pauseAnimation': self._on_pause_animation,
            'stopAnimation': self._on_stop_animation,
            # live temperature data forwarded by the web client
            'updateGasifierTelemetry': self._on_update_gasifier_telemetry,
            # web-style left-button camera orbit
            'orbitCamera': self._on_orbit_camera,
        }

        ed = get_eventdispatcher()
        for event_type, handler in incoming.items():
            omni.kit.app.register_event_alias(
                carb.events.type_from_string(event_type),
                event_type,
            )
            self._subscriptions.append(
                ed.observe_event(
                    observer_name=f"StageManager:{event_type}",
                    event_name=event_type,
                    on_event=handler,
                )
            )

        # -- subscribe to stage events
        usd_context = omni.usd.get_context()
        event_stream = omni.usd.get_context().get_stage_event_stream()
        self._subscriptions.append(
            ed.observe_event(
                observer_name="StageManager:StageOpened",
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=self._on_stage_event_opened,
            )
        )
        self._subscriptions.append(
            ed.observe_event(
                observer_name="StageManager:SelectionChanged",
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.SELECTION_CHANGED),
                on_event=self._on_stage_event_selection_changed,
            )
        )
        if carb.settings.get_settings().get_as_bool("/app/gasifier/enableSampleTelemetry"):
            self._sample_telemetry_task = asyncio.ensure_future(self._run_sample_telemetry())

    async def _run_sample_telemetry(self):
        """Drive the live CFD field directly in Kit every ten seconds."""
        step = 0
        # Wait for the setup extension to finish opening the stage.
        await asyncio.sleep(5.0)
        while True:
            phase = step * 0.72
            step += 1
            telemetry = {
                "reactor_dryingZoneTemperatureC": round(326.3 + 28.0 * math.sin(phase), 1),
                "reactor_pyrolysisZoneTemperatureC": round(565.1 + 52.0 * math.sin(phase + 0.7), 1),
                "reactor_combustionZoneTemperatureC": round(875.0 + 58.0 * math.sin(phase + 1.2), 1),
                "reactor_reductionZoneTemperatureC": round(707.2 + 47.0 * math.sin(phase + 1.8), 1),
                "reactor_ashZoneTemperatureC": round(390.6 + 34.0 * math.sin(phase + 2.4), 1),
                "reactor_gasOutletTemperatureC": round(316.1 + 24.0 * math.sin(phase + 2.9), 1),
            }
            get_eventdispatcher().dispatch_event(
                "updateGasifierTelemetry", payload={"telemetry": telemetry}
            )
            await asyncio.sleep(10.0)
    def get_children(self, prim_path, filters=None):
        """
        Collect any children of the given `prim_path`, potentially filtered by `filters`
        """
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            return []

        filter_types = {
            "USDGeom": UsdGeom.Mesh,
            "mesh": UsdGeom.Mesh,
            "xform": UsdGeom.Xform,
            "scope": UsdGeom.Scope,
        }

        if isinstance(filters, carb.dictionary.Item):
            filters = filters.get_dict()
        # The web client intentionally sends [] to request every prim type.
        # Only apply schema filtering when at least one filter was supplied.
        active_filters = list(filters) if filters else []

        children = []
        for child in prim.GetChildren():
            # If a child doesn't pass any filter, we skip it.
            if active_filters:
                if not any(child.IsA(filter_types[filt]) for filt in active_filters if filt in filter_types):
                    continue

            child_name = child.GetName()
            child_path = str(prim.GetPath())
            # Skipping over cameras
            if child_name.startswith('OmniverseKit_'):
                continue
            # Also skipping rendering primitives.
            if prim_path == '/' and child_name == 'Render':
                continue
            child_path = child_path if child_path != '/' else ''
            carb.log_info(f'child_path: {child_path}')
            info = {
                "name": child_name,
                "path": f'{child_path}/{child_name}',
                "type": child.GetTypeName() or "Scope",
            }

            # We return an empty list here to indicate that children are
            # available, but the current app does not support pagination,
            # so we use this to lazy load the stage tree.
            if child.GetChildren():
                info["children"] = []

            children.append(info)

        return children

    def _on_get_children(self, event: carb.events.IEvent) -> None:
        """
        Handler for the `getChildrenRequest` event
        Collects a filtered collection of a given primitives children.
        """

        carb.log_info(
            "Received message to return list of a prim\'s children"
        )
        children = self.get_children(
            prim_path=event.payload["prim_path"],
            filters=event.payload["filters"]
        )
        payload = {
            "prim_path": event.payload["prim_path"],
            "children": children
        }


        get_eventdispatcher().dispatch_event("getChildrenResponse", payload=payload)

    def _on_select_prims(self, event: carb.events.IEvent) -> None:
        """
        Handler for `selectPrimsRequest` event.

        Selects the given primitives.
        """
        new_selection = []
        if "paths" in event.payload:
            if isinstance(event.payload["paths"], carb.dictionary.Item):
                new_selection = list(event.payload["paths"].get_dict())
            else:
                new_selection = list(event.payload["paths"])
            carb.log_info(f"Received message to select '{new_selection}'")
        # Flagging this as an external event because it
        # was initiated by the client.
        self._is_external_update = True
        sel = omni.usd.get_context().get_selection()
        sel.clear_selected_prim_paths()
        sel.set_selected_prim_paths(new_selection, True)

    def _on_stage_event_opened(self, event):
        stage = omni.usd.get_context().get_stage()
        stage_url = stage.GetRootLayer().identifier if stage else ''

        if stage_url:
            # Enable global pickability by default so all objects can be selected
            ctx = omni.usd.get_context()
            ctx.set_pickable("/", True)
            carb.log_info(f"StageManager: Enabled global pickability for stage: {stage_url}")
            # Clear before using, so that we're sure the data is only
            # from the new stage.
            self._camera_attrs.clear()
            self._orbit_state = None
            # Capture the active camera's camera data, used to reset
            # the scene to a known good state.
            if (prim := ctx.get_stage().GetPrimAtPath(get_active_viewport_camera_string())):
                for attr in prim.GetAttributes():
                    self._camera_attrs[attr.GetName()] = attr.Get()

    def _on_stage_event_selection_changed(self, event):
        # If the selection changed came from an external event,
        # we don't need to let the streaming client know because it
        # initiated the change and is already aware.
        if self._is_external_update:
            self._is_external_update = False
        else:
            payload = {"prims": omni.usd.get_context().get_selection().
                        get_selected_prim_paths()}

            get_eventdispatcher().dispatch_event("stageSelectionChanged", payload=payload)
            carb.log_info(f"UI_DEBUG_SERVER: Selection changed: {payload['prims']}")

    def _on_reset_camera(self, event: carb.events.IEvent):
        """
        Handler for `resetStage` event.

        Resets the camera back to values collected when the stage was opened.
        A success message is sent if all attributes are succesfully reset, and error message is set otherwise.
        """
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        try:
            # Reset the camera.
            # The camera lives on the session layer, which has a higher
            # opinion than the root stage. So we need to explicitly target
            # the session layer when resetting the camera's attributes.
            camera_prim = ctx.get_stage().GetPrimAtPath(
                get_active_viewport_camera_string()
            )
            edit_context = Usd.EditContext(
                stage, Usd.EditTarget(stage.GetSessionLayer())
            )
            with edit_context:
                for name, value in self._camera_attrs.items():
                    attr = camera_prim.GetAttribute(name)
                    attr.Set(value)
        except Exception as e:
            payload = {"result": "error", "error": str(e)}
        else:
            self._orbit_state = None
            payload = {"result": "success", "error": ""}

        get_eventdispatcher().dispatch_event("resetStageResponse", payload=payload)

    def _on_make_pickable(self, event: carb.events.IEvent):
        """
        Handler for `makePrimsPickable` event.
        Enables viewport selection for the provided primitives.
        """
        ctx = omni.usd.get_context()
        # We no longer force the entire stage to False here to avoid locking out 3D clicks
        # Set the provided paths to be pickable.
        try:
            if "paths" in event.payload:
                if isinstance(event.payload["paths"], carb.dictionary.Item):
                    paths = list(event.payload["paths"].get_dict())
                else:
                    paths = list(event.payload["paths"])

            for path in paths:
                ctx.set_pickable(path, True)
        except Exception as e:
            payload = {"result": "error", "error": str(e)}
        else:
            payload = {"result": "success", "error": ""}

        get_eventdispatcher().dispatch_event("makePrimsPickableResponse", payload=payload)

    def _on_frame_selection(self, event: carb.events.IEvent):
        """
        Handler for `frameSelection` event.
        Frames the current selection in the viewport.
        """
        carb.log_info("Received message to frame selection")
        try:
            # Use the programmatic API instead of the command to avoid registration issues
            omni.kit.viewport.utility.frame_viewport_selection()
            self._orbit_state = None
        except Exception as e:
            carb.log_error(f"Failed to frame selection: {str(e)}")

    def _on_orbit_camera(self, event: carb.events.IEvent):
        """Orbit the active camera around the loaded stage using mouse deltas."""
        try:
            payload = self._payload_to_dict(event.payload)
            delta_x = max(-120.0, min(120.0, float(payload.get("deltaX", 0.0))))
            delta_y = max(-120.0, min(120.0, float(payload.get("deltaY", 0.0))))
            stage = omni.usd.get_context().get_stage()
            camera_prim = stage.GetPrimAtPath(get_active_viewport_camera_string()) if stage else None
            if not camera_prim or not camera_prim.IsA(UsdGeom.Camera):
                raise RuntimeError("The active viewport camera is unavailable")

            up_axis = UsdGeom.GetStageUpAxis(stage)
            if self._orbit_state is None:
                bounds = UsdGeom.BBoxCache(
                    Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]
                ).ComputeWorldBound(stage.GetDefaultPrim() or stage.GetPseudoRoot()).ComputeAlignedRange()
                target = bounds.GetMidpoint()
                camera_world = UsdGeom.Xformable(camera_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                eye = camera_world.ExtractTranslation()
                offset = eye - target
                radius = max(0.1, offset.GetLength())
                if up_axis == UsdGeom.Tokens.y:
                    yaw = math.atan2(offset[0], offset[2])
                    pitch = math.asin(max(-1.0, min(1.0, offset[1] / radius)))
                else:
                    yaw = math.atan2(offset[1], offset[0])
                    pitch = math.asin(max(-1.0, min(1.0, offset[2] / radius)))
                self._orbit_state = [target, radius, yaw, pitch, up_axis]

            target, radius, yaw, pitch, up_axis = self._orbit_state
            yaw -= delta_x * 0.006
            pitch = max(math.radians(-85.0), min(math.radians(85.0), pitch + delta_y * 0.006))
            cosine = math.cos(pitch)
            if up_axis == UsdGeom.Tokens.y:
                eye = target + Gf.Vec3d(
                    radius * math.sin(yaw) * cosine,
                    radius * math.sin(pitch),
                    radius * math.cos(yaw) * cosine,
                )
                up = Gf.Vec3d(0.0, 1.0, 0.0)
            else:
                eye = target + Gf.Vec3d(
                    radius * math.cos(yaw) * cosine,
                    radius * math.sin(yaw) * cosine,
                    radius * math.sin(pitch),
                )
                up = Gf.Vec3d(0.0, 0.0, 1.0)
            camera_to_world = Gf.Matrix4d().SetLookAt(eye, target, up).GetInverse()
            with Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer())):
                UsdGeom.Xformable(camera_prim).MakeMatrixXform().Set(camera_to_world)
            self._orbit_state = [target, radius, yaw, pitch, up_axis]
        except Exception as exc:
            carb.log_error(f"Failed to orbit camera: {exc}")

    def _on_play_animation(self, event: carb.events.IEvent):
        """
        Handler for `playAnimation` event.
        Starts playback of the USD animation timeline.
        """
        carb.log_info("Received message to play animation")
        try:
            import omni.timeline
            timeline = omni.timeline.get_timeline_interface()
            timeline.play()
            carb.log_info("Animation playback started.")
        except Exception as e:
            carb.log_error(f"Failed to play animation: {str(e)}")

    def _on_pause_animation(self, event: carb.events.IEvent):
        """
        Handler for `pauseAnimation` event.
        Pauses playback of the USD animation timeline.
        """
        carb.log_info("Received message to pause animation")
        try:
            import omni.timeline
            timeline = omni.timeline.get_timeline_interface()
            timeline.pause()
            carb.log_info("Animation paused.")
        except Exception as e:
            carb.log_error(f"Failed to pause animation: {str(e)}")

    def _on_stop_animation(self, event: carb.events.IEvent):
        """
        Handler for `stopAnimation` event.
        Stops playback and resets timeline to frame 0.
        """
        carb.log_info("Received message to stop animation")
        try:
            import omni.timeline
            timeline = omni.timeline.get_timeline_interface()
            timeline.stop()
            carb.log_info("Animation stopped and reset to frame 0.")
        except Exception as e:
            carb.log_error(f"Failed to stop animation: {str(e)}")

    @staticmethod
    def _payload_to_dict(value):
        """Convert Carbonite dictionary values into ordinary Python values."""
        if isinstance(value, carb.dictionary.Item):
            value = value.get_dict()
        if isinstance(value, dict):
            return {str(key): StageManager._payload_to_dict(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [StageManager._payload_to_dict(item) for item in value]
        return value

    @staticmethod
    def _temperature_color(value, minimum, maximum):
        span = max(1.0e-6, maximum - minimum)
        normalized = max(0.0, min(1.0, (value - minimum) / span))
        return Gf.Vec3f(*colorsys.hsv_to_rgb((1.0 - normalized) * 0.67, 0.92, 1.0))

    @staticmethod
    def _interpolate_axial_temperature(z, profile):
        for (z0, t0), (z1, t1) in zip(profile, profile[1:]):
            if z <= z1:
                amount = max(0.0, min(1.0, (z - z0) / (z1 - z0)))
                amount = amount * amount * (3.0 - 2.0 * amount)
                return t0 + (t1 - t0) * amount
        return profile[-1][1]

    def _on_update_gasifier_telemetry(self, event: carb.events.IEvent):
        """Recolor the existing CFD mesh from six live zone temperatures."""
        aliases = {
            "DryingZone": ("reactor_dryingZoneTemperatureC", "drying", "Drying", "DryingZone"),
            "PyrolysisZone": ("reactor_pyrolysisZoneTemperatureC", "pyrolysis", "Pyrolysis", "PyrolysisZone"),
            "CombustionZone": ("reactor_combustionZoneTemperatureC", "combustion", "Combustion", "CombustionZone"),
            "ReductionZone": ("reactor_reductionZoneTemperatureC", "reduction", "Reduction", "ReductionZone"),
            "AshZone": ("reactor_ashZoneTemperatureC", "ash", "Ash", "AshZone"),
            "Outlet": ("reactor_gasOutletTemperatureC", "outlet", "gasOutlet", "Outlet"),
        }
        try:
            payload = self._payload_to_dict(event.payload)
            color_scale = payload.get("colorScale", {})
            telemetry = payload.get("telemetry", payload)
            if isinstance(telemetry.get("data"), dict):
                telemetry = {**telemetry, **telemetry["data"]}
            if isinstance(telemetry.get("temperatures"), dict):
                telemetry = {**telemetry, **telemetry["temperatures"]}

            temperatures = {}
            for zone, keys in aliases.items():
                raw_value = next((telemetry[key] for key in keys if key in telemetry), None)
                if raw_value is None:
                    raise ValueError(f"Missing temperature for {zone}; accepted keys: {', '.join(keys)}")
                value = float(raw_value)
                if not math.isfinite(value) or value < -273.15 or value > 2500.0:
                    raise ValueError(f"Invalid {zone} temperature: {raw_value}")
                temperatures[zone] = value

            scale_min = float(color_scale.get("min", min(temperatures.values())))
            scale_max = float(color_scale.get("max", max(temperatures.values())))
            if not math.isfinite(scale_min) or not math.isfinite(scale_max) or scale_max <= scale_min:
                raise ValueError(f"Invalid color scale: {scale_min}..{scale_max}")

            stage = omni.usd.get_context().get_stage()
            if not stage:
                raise RuntimeError("No USD stage is open")
            field_root = stage.GetPrimAtPath("/Gasifier/TemperatureField")
            fields = [
                prim for prim in field_root.GetChildren()
                if prim.IsA(UsdGeom.Mesh)
            ] if field_root else []
            # Also support the generated gasifier_cfd.usd hierarchy.
            single_field = stage.GetPrimAtPath("/Gasifier/TemperatureField/Field")
            if single_field and single_field.IsA(UsdGeom.Mesh) and single_field not in fields:
                fields.append(single_field)
            if not fields:
                raise RuntimeError("No CFD meshes were found below /Gasifier/TemperatureField")

            profile = [
                (0.15, temperatures["Outlet"]),
                (1.5, temperatures["AshZone"]),
                (3.7, temperatures["ReductionZone"]),
                (6.0, temperatures["CombustionZone"]),
                (8.4, temperatures["PyrolysisZone"]),
                (10.8, temperatures["DryingZone"]),
            ]
            with Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer())):
                for field in fields:
                    field_values = []
                    colors = []
                    points = UsdGeom.Mesh(field).GetPointsAttr().Get() or []
                    for point in points:
                        # gasifier.usda is Y-up; gasifier_cfd.usd is Z-up.
                        is_y_up = UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.y
                        if is_y_up:
                            x, axial, radial_other = point
                        else:
                            x, radial_other, axial = point
                        radius = min(1.0, math.hypot(x, radial_other) / 1.25)
                        combustion_weight = math.exp(-((axial - 3.0) / 1.05) ** 2)
                        wall_loss = radius ** 1.65 * (10.0 + 38.0 * combustion_weight)
                        theta = math.atan2(radial_other, x)
                        asymmetry = radius * (2.0 + 5.0 * combustion_weight) * (
                            0.5 + 0.5 * math.sin(2.0 * theta + 0.7 * axial)
                        )
                        # gasifier.usda spans Y=0..6, so map it onto the
                        # generator's 0.15..10.8 telemetry profile.
                        profile_position = (
                            0.15 + max(0.0, min(6.0, axial)) * (10.65 / 6.0)
                            if is_y_up else axial
                        )
                        value = self._interpolate_axial_temperature(profile_position, profile)
                        value -= wall_loss + asymmetry
                        value = max(scale_min, min(scale_max, value))
                        field_values.append(value)
                        colors.append(self._temperature_color(value, scale_min, scale_max))
                    temperature_attr = field.GetAttribute("field:temperature")
                    if temperature_attr:
                        temperature_attr.Set(field_values)
                    field.GetAttribute("primvars:displayColor").Set(colors)
                for zone in ("DryingZone", "PyrolysisZone", "CombustionZone", "ReductionZone", "AshZone"):
                    zone_prim = stage.GetPrimAtPath(f"/Gasifier/Reactor/{zone}")
                    if zone_prim:
                        zone_attr = zone_prim.GetAttribute("telemetry:temperature")
                        if zone_attr:
                            zone_attr.Set(temperatures[zone])
                outlet_prim = stage.GetPrimAtPath("/Gasifier/GasOutlet")
                if outlet_prim:
                    outlet_attr = outlet_prim.GetAttribute("telemetry:temperature")
                    if outlet_attr:
                        outlet_attr.Set(temperatures["Outlet"])

            response = {"result": "success", "temperatures": temperatures, "colorScale": {"min": scale_min, "max": scale_max}}
            status = (
                f"[{time.strftime('%H:%M:%S')}] [Gasifier CFD] Gradient updated | "
                f"Drying={temperatures['DryingZone']:.1f} C | "
                f"Pyrolysis={temperatures['PyrolysisZone']:.1f} C | "
                f"Combustion={temperatures['CombustionZone']:.1f} C | "
                f"Reduction={temperatures['ReductionZone']:.1f} C | "
                f"Ash={temperatures['AshZone']:.1f} C | "
                f"Outlet={temperatures['Outlet']:.1f} C | meshes={len(fields)}"
            )
            print(status, flush=True)
            carb.log_info(status)
        except Exception as exc:
            response = {"result": "error", "error": str(exc)}
            carb.log_error(f"Failed to update gasifier telemetry: {exc}")
        get_eventdispatcher().dispatch_event("gasifierTelemetryUpdated", payload=response)

    def on_shutdown(self):
        """This is called every time the extension is deactivated. It is used
        to clean up the extension state."""
        # Reseting the state.
        self._subscriptions.clear()
        if self._sample_telemetry_task:
            self._sample_telemetry_task.cancel()
            self._sample_telemetry_task = None
        self._is_external_update: bool = False
        self._camera_attrs.clear()
        self._orbit_state = None
