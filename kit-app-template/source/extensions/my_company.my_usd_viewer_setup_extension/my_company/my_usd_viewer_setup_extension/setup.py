# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
from pathlib import Path

import carb.settings
import carb.tokens
import omni.ext
import omni.kit.app
import omni.kit.imgui as _imgui
import omni.usd
from omni.kit.mainwindow import get_main_window
from omni.kit.quicklayout import QuickLayout
from omni.kit.viewport.utility import get_active_viewport_camera_string, get_viewport_from_window_name, frame_viewport_selection

COMMAND_MACRO_SETTING = "/exts/omni.kit.command_macro.core/"
COMMAND_MACRO_FILE_SETTING = COMMAND_MACRO_SETTING + "macro_file"


async def _load_layout(layout_file: str):
    """Loads a provided layout file and ensures the viewport is set to FILL."""
    await omni.kit.app.get_app().next_update_async()
    QuickLayout.load_file(layout_file)

    # Set viewport to FILL
    viewport_api = get_viewport_from_window_name("Viewport")
    if viewport_api and hasattr(viewport_api, "fill_frame"):
        viewport_api.fill_frame = True


class SetupExtension(omni.ext.IExt):
    """Extension that sets up the USD Viewer application."""

    def _apply_background(self):
        """Apply the viewport background after renderer/stage initialization."""
        # Calibrated RTX-linear value that tone-maps to the web #0d1418.
        background_color = (0.012, 0.019, 0.024)
        self._settings.set("/rtx/renderer/clearColor", background_color)
        # RTX otherwise prefers the DomeLight as the visible background.
        self._settings.set("/rtx/background/source/type", 2)
        self._settings.set("/rtx/background/source/color", background_color)
        self._settings.set("/rtx/post/background/color", background_color)
        self._settings.set("/rtx/post/background/useBackground", True)
        self._settings.set("/rtx/post/background/colorMode", 1)
        self._settings.set("/rtx/post/background/alpha", 1.0)

    def on_startup(self, _ext_id: str):
        """This is called every time the extension is activated. It is used to
        set up the application and load the stage."""
        self._settings = carb.settings.get_settings()
        # Match the web viewer panels exactly (#0d1418).
        self._apply_background()
        self._settings.set("/rtx/hydra/enabledVisualizer", "")  # Disable any weird visualizers
        self._settings.set("/app/viewport/grid/enabled", False)  # Disable the grid
        self._settings.set("/rtx/eco/enabled", False)          # Disable eco mode if washing out pixels

        if self._settings and self._settings.get("/app/warmupMode"):
            # if warmup mode is enabled, we don't want to load the stage just return
            return
        # get auto load stage name
        stage_url = self._settings.get_as_string("/app/auto_load_usd")

        # check if setup have benchmark macro file to activate - ignore setup
        # auto_load_usd name, in order to run proper benchmark.
        benchmark_macro_file_name = self._settings.get(
            COMMAND_MACRO_FILE_SETTING)
        if benchmark_macro_file_name:
            stage_url = None

        # if no benchmark is activated (not applicable on production -
        # provided macro file name will always be None) -
        # load provided by setup stage.
        if stage_url:
            stage_url = carb.tokens.get_tokens_interface().resolve(stage_url)
            try:
                path = Path(stage_url)
                if path.exists():
                    stage_url = str(path.resolve())
            except (OSError, RuntimeError):
                # Keep original stage_url - it might be a valid URL or network path
                pass
            asyncio.ensure_future(self.__open_stage(stage_url))

        self._await_layout = asyncio.ensure_future(self._delayed_layout())
        get_main_window().get_main_menu_bar().visible = False

    async def _delayed_layout(self):
        """This function is used to delay the layout loading until the
        application has finished its initial setup."""
        main_menu_bar = get_main_window().get_main_menu_bar()
        main_menu_bar.visible = False
        # few frame delay to allow automatic Layout of window that want their
        # own positions
        app = omni.kit.app.get_app()
        for _ in range(4):
            await app.next_update_async()  # type: ignore

        settings = carb.settings.get_settings()
        # setup the Layout for your app
        token = "${my_company.my_usd_viewer_setup_extension}/layouts"

        layouts_path = carb.tokens.get_tokens_interface().resolve(token)
        layout_name = settings.get("/app/layout/name")
        layout_file = Path(layouts_path).joinpath(f"{layout_name}.json")

        asyncio.ensure_future(_load_layout(f"{layout_file}"))

        # using imgui directly to adjust some color and Variable
        imgui = _imgui.acquire_imgui()

        # DockSplitterSize is the variable that drive the size of the
        # Dock Split connection
        imgui.push_style_var_float(_imgui.StyleVar.DockSplitterSize, 2)

    async def __open_stage(self, url, frame_delay: int = 5):
        """Opens the provided USD stage and loads the render settings."""
        # default 5 frame delay to allow for Layout
        if frame_delay:
            app = omni.kit.app.get_app()
            for _ in range(frame_delay):
                await app.next_update_async()

        usd_context = omni.usd.get_context()

        count = 0
        timed_out = False
        # Wait until we can open the stage
        while not usd_context.can_open_stage():
            await omni.kit.app.get_app().next_update_async()
            count += 1
            if count > 100:
                timed_out = True
                break

        if not timed_out:
            await usd_context.open_stage_async(
                url, omni.usd.UsdContextInitialLoadSet.LOAD_ALL)
        else:
            carb.log_warn(
                f"SetupExtension: Timed out waiting to open stage {url}")
            return

        # [DISABLED] Stage-provided render settings can cause instability or 
        # inappropriate performance settings for streaming. We use app defaults.
        # if not bool(self._settings.get("/app/content/emptyStageOnStart")):
        #    usd_context.load_render_settings_from_stage(
        #        usd_context.get_stage_id())

        # 1. Wait longer for assets to load and renderer to initialize
        for _ in range(120): # ~2 seconds at 60fps
            await omni.kit.app.get_app().next_update_async()

        # Renderer startup and stage loading can replace post-process settings.
        self._apply_background()

        # 2. Add lighting if missing (RTX needs a light to show anything)
        try:
            from pxr import UsdGeom
            stage = usd_context.get_stage()
            # The authored transparent cylinder produces dark vertical facet
            # bands in RTX streaming. The internal CFD mesh already supplies
            # the visible reactor volume, so hide only this redundant shell.
            reactor_shell = stage.GetPrimAtPath("/Gasifier/Reactor/Shell")
            if reactor_shell:
                UsdGeom.Imageable(reactor_shell).MakeInvisible()
            # Most robust check: check for any prim that has "Light" in its type name
            lights = [p for p in stage.Traverse() if "Light" in p.GetTypeName()]
            if not lights:
                carb.log_warn("SetupExtension: No lights found. Adding default DomeLight.")
                from pxr import UsdLux
                # Use Define instead of DefineAttribute or similar to be safe
                dome_light = UsdLux.DomeLight.Define(stage, "/DefaultDomeLight")
                # Use the older GetAttribute style for better compatibility
                if dome_light.GetIntensityAttr():
                    dome_light.GetIntensityAttr().Set(500)
                if dome_light.GetExposureAttr():
                    dome_light.GetExposureAttr().Set(0.0)

            self._apply_background()
        except Exception as e:
            carb.log_error(f"SetupExtension: Failed to add light: {e}")

        # 3. Auto-frame the viewport so the scene is visible immediately
        try:
            viewport_api = get_viewport_from_window_name("Viewport")
            if viewport_api:
                # Use BBoxCache instead of GetStageBoundingBox (much more reliable)
                from pxr import UsdGeom, Usd
                stage = usd_context.get_stage()
                bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default"])
                range_ = bbox_cache.ComputeWorldBound(stage.GetPseudoRoot()).GetRange()
                
                diag_file = Path(carb.tokens.get_tokens_interface().resolve("${app}/../stage_diagnostics.txt"))
                hierarchy_file = Path(carb.tokens.get_tokens_interface().resolve("${app}/../factory_hierarchy.txt"))
                with open(diag_file, "w") as f:
                    f.write(f"Stage: {url}\n")
                    f.write(f"BBox Min: {range_.GetMin()}, Max: {range_.GetMax()}\n")
                    f.write(f"Up Axis: {UsdGeom.GetStageUpAxis(stage)}\n")
                    f.write(f"MetersPerUnit: {UsdGeom.GetStageMetersPerUnit(stage)}\n")
                    f.write(f"Cameras: {[p.GetPath() for p in stage.Traverse() if p.IsA(UsdGeom.Camera)]}\n")
                    f.write(f"Lights: {[p.GetPath() for p in stage.Traverse() if 'Light' in p.GetTypeName()]}\n")

                with open(hierarchy_file, "w") as f:
                    f.write(f"Top-level hierarchy for {url}:\n")
                    for prim in stage.Traverse():
                        depth = len(prim.GetPath().pathString.split('/')) - 1
                        if depth <= 4:
                            indent = "  " * depth
                            f.write(f"{indent}{prim.GetPath()} [{prim.GetTypeName()}]\n")

                carb.log_info(f"SetupExtension: Diagnostic data written to {diag_file}")
                carb.log_info(f"SetupExtension: Hierarchy data written to {hierarchy_file}")
                
                carb.log_info("SetupExtension: Initial Framing.")
                omni.usd.get_context().get_selection().clear_selected_prim_paths()
                from omni.kit.viewport.utility import frame_viewport_selection
                frame_viewport_selection(viewport_api)
                
                # Double-frame after another short delay to handle late-loading geometry
                for _ in range(60): # 1 second delay
                    await omni.kit.app.get_app().next_update_async()
                carb.log_info("SetupExtension: Final Framing Adjustment.")
                frame_viewport_selection(viewport_api)

                # Deterministic straight-on front view for the Y-up gasifier.
                # The camera remains freely orbitable after this initial pose.
                from pxr import Gf
                camera_prim = stage.GetPrimAtPath(get_active_viewport_camera_string())
                if camera_prim and camera_prim.IsA(UsdGeom.Camera):
                    target = range_.GetMidpoint()
                    size = range_.GetSize()
                    if UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.y:
                        eye = target + Gf.Vec3d(0.0, 0.0, max(size[1] * 2.0, size[0] * 2.35))
                        up = Gf.Vec3d(0.0, 1.0, 0.0)
                    else:
                        eye = target + Gf.Vec3d(0.0, -max(size[2] * 2.0, size[0] * 2.35), 0.0)
                        up = Gf.Vec3d(0.0, 0.0, 1.0)
                    camera_matrix = Gf.Matrix4d().SetLookAt(eye, target, up).GetInverse()
                    with Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer())):
                        UsdGeom.Xformable(camera_prim).MakeMatrixXform().Set(camera_matrix)
                    carb.log_info("SetupExtension: Applied straight-on gasifier camera pose.")
        except Exception as e:
            carb.log_error(f"SetupExtension: Failed to frame viewport: {e}")

    def on_shutdown(self):
        """This is called every time the extension is deactivated."""
        return
