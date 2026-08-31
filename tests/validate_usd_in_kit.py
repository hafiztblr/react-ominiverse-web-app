"""Run with Kit's --exec option to validate a generated CFD stage."""

import carb.settings
import omni.kit.app
from pxr import Sdf, Usd, UsdGeom, UsdShade
import traceback


def main() -> None:
    path = carb.settings.get_settings().get("/cfd/validationStage")
    if not path:
        raise RuntimeError("Pass --/cfd/validationStage=<absolute path>")
    layer = Sdf.Layer.FindOrOpen(path)
    if not layer:
        raise RuntimeError(f"Kit/Sdf could not parse {path}")
    stage = Usd.Stage.Open(path)
    mesh = UsdGeom.Mesh.Get(stage, "/World/CFD/Mesh")
    if not mesh:
        raise RuntimeError("Composed /World/CFD/Mesh was not found")
    if len(mesh.GetFaceVertexCountsAttr().Get()) != 700:
        raise RuntimeError("Expected 700 composed faces")
    temperature = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("Gas_temperature")
    if not temperature or temperature.GetInterpolation() != UsdGeom.Tokens.uniform:
        raise RuntimeError("Gas_temperature is not a uniform primvar")
    if temperature.ValueMightBeTimeVarying():
        # Frame 0000 is legitimately constant; validate a later authored sample.
        sample_time = min(stage.GetStartTimeCode() + 10, stage.GetEndTimeCode())
        time_code = Usd.TimeCode(sample_time)
    else:
        time_code = Usd.TimeCode.Default()
    temperature_values = temperature.Get(time_code)
    if len(temperature_values) != 700:
        raise RuntimeError("Expected 700 Gas_temperature values")
    display_color = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("displayColor")
    if not display_color or display_color.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        raise RuntimeError("displayColor is not a faceVarying render primvar")
    colors = display_color.Get(time_code)
    if len(colors) != 2800 or len(set(tuple(color) for color in colors)) <= 1:
        raise RuntimeError("Expected 2800 non-constant per-corner temperature colors")
    camera = UsdGeom.Camera.Get(stage, "/World/CFD/Camera")
    backdrop = UsdGeom.Mesh.Get(stage, "/World/CFD/Backdrop")
    if not camera or camera.GetProjectionAttr().Get() != UsdGeom.Tokens.orthographic:
        raise RuntimeError("Expected the CFD orthographic front camera")
    if not backdrop or len(backdrop.GetFaceVertexCountsAttr().Get()) != 1:
        raise RuntimeError("Expected the CFD dark backdrop")
    material, _ = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial()
    if not material or material.GetPath() != Sdf.Path("/World/CFD/Looks/TemperatureMaterial"):
        raise RuntimeError("Expected the emissive CFD temperature material binding")
    print("KIT USD VALIDATION: PASS")
    print(f"Layer: {layer.identifier}")
    print(f"Faces: {len(mesh.GetFaceVertexCountsAttr().Get())}")
    print(f"Gas_temperature values: {len(temperature_values)}")
    print(f"Time range: {stage.GetStartTimeCode()} to {stage.GetEndTimeCode()}")
    print(f"Validated time: {time_code.GetValue()}")
    print(f"Distinct display colors: {len(set(tuple(color) for color in colors))}")
    print(f"Camera: {camera.GetPath()} ({camera.GetProjectionAttr().Get()})")
    print(f"Material: {material.GetPath()}")


try:
    main()
except Exception:
    traceback.print_exc()
    omni.kit.app.get_app().post_quit(1)
else:
    omni.kit.app.get_app().post_quit(0)
