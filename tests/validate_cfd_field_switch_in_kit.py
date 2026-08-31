"""Kit runtime validation for dynamic CFD field recoloring."""

import asyncio
import traceback

from carb.eventdispatcher import get_eventdispatcher
import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom


async def validate():
    try:
        for _ in range(600):
            stage = omni.usd.get_context().get_stage()
            if stage and stage.GetPrimAtPath("/World/CFD/Mesh"):
                break
            await omni.kit.app.get_app().next_update_async()
        else:
            raise RuntimeError("CFD stage did not open")

        get_eventdispatcher().dispatch_event(
            "setCFDField", payload={"field": "CO2_Gas_mass_fractions_5"}
        )
        await omni.kit.app.get_app().next_update_async()
        mesh = UsdGeom.Mesh.Get(stage, "/World/CFD/Mesh")
        display = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("displayColor")
        colors = display.Get(Usd.TimeCode(10))
        if display.GetInterpolation() != UsdGeom.Tokens.faceVarying:
            raise RuntimeError("Dynamic displayColor is not faceVarying")
        if len(colors) != 2800 or len(set(tuple(color) for color in colors)) <= 1:
            raise RuntimeError("Dynamic CO2 recoloring did not produce per-cell colors")
        print("KIT CFD FIELD SWITCH: PASS")
        print(f"CO2 colors at t=10: {len(colors)} corners, {len(set(tuple(c) for c in colors))} distinct")
        omni.kit.app.get_app().post_quit(0)
    except Exception:
        traceback.print_exc()
        omni.kit.app.get_app().post_quit(1)


asyncio.ensure_future(validate())
