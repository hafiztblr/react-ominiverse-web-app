"""OpenUSD-runtime validation; run with Kit's ``--exec`` option."""

import sys
from pathlib import Path

from pxr import Usd, UsdGeom


path = Path(__file__).resolve().parents[1] / "source" / "examples" / "gasifier_cfd.usd"
stage = Usd.Stage.Open(str(path))
if not stage:
    raise RuntimeError(f"Could not open {path}")

required = [
    "/Gasifier/Geometry/ReactorShell",
    "/Gasifier/Reactor/CombustionZone",
    "/Gasifier/TemperatureField/Field",
    "/Gasifier/SyngasFlow/H2",
    "/Gasifier/GasOutlet",
]
for prim_path in required:
    if not stage.GetPrimAtPath(prim_path):
        raise RuntimeError(f"Missing required prim: {prim_path}")

field = UsdGeom.Mesh.Get(stage, "/Gasifier/TemperatureField/Field")
if len(field.GetPointsAttr().Get()) < 2500:
    raise RuntimeError("Temperature field is unexpectedly sparse")
if not field.GetFaceVertexIndicesAttr().Get():
    raise RuntimeError("Temperature contour mesh has no faces")
bindings = field.GetPrim().GetRelationship("material:binding").GetTargets()
if str(bindings[0]) != "/Gasifier/Looks/TemperatureMaterial":
    raise RuntimeError(f"Temperature field material is not bound correctly: {bindings}")
colors = field.GetPrim().GetAttribute("primvars:displayColor").Get()
if not colors or max(c[0] for c in colors) < 0.9 or max(c[2] for c in colors) < 0.9:
    raise RuntimeError("Temperature field does not contain both hot and cold color ranges")
if stage.GetEndTimeCode() != 96 or not stage.GetPrimAtPath("/Gasifier/SyngasFlow/H2").GetAttribute("points").GetTimeSamples():
    raise RuntimeError("Animation time samples are missing")

particles = UsdGeom.Points.Get(stage, "/Gasifier/SyngasFlow/H2")
sample_times = particles.GetPointsAttr().GetTimeSamples()
if sample_times != list(range(0, 97, 8)):
    raise RuntimeError(f"Unexpected syngas path samples: {sample_times}")
for time in sample_times:
    for point in particles.GetPointsAttr().Get(time):
        x, y, z = point
        if time <= 64 and (x * x + y * y) ** 0.5 >= 1.7:
            raise RuntimeError(f"Particle leaves reactor at time {time}: {point}")
        if time >= 72 and abs(y) > 0.12:
            raise RuntimeError(f"Particle leaves outlet/cooler path at time {time}: {point}")

print(f"OpenUSD validation passed: {path}")
print(f"Prims: {sum(1 for _ in stage.Traverse())}; field vertices: {len(field.GetPointsAttr().Get())}")

try:
    import omni.kit.app
    omni.kit.app.get_app().post_quit(0)
except ImportError:
    pass
