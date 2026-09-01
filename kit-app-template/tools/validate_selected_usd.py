"""Validate the user-selected gasifier.usda with the bundled Kit runtime."""

from pathlib import Path

from pxr import Usd


path = Path(__file__).resolve().parents[2] / "gasifier.usda"
stage = Usd.Stage.Open(str(path))
if not stage:
    raise RuntimeError(f"Could not open {path}")
default_prim = stage.GetDefaultPrim()
if not default_prim or default_prim.GetPath().pathString != "/Gasifier":
    raise RuntimeError("gasifier.usda must have /Gasifier as its default prim")
prim_count = sum(1 for _ in stage.Traverse())
if prim_count < 10:
    raise RuntimeError(f"Stage is unexpectedly empty ({prim_count} prims)")
print(f"Selected USD validation passed: {path}")
print(f"Default prim: {default_prim.GetPath()}; prims: {prim_count}")

try:
    import omni.kit.app
    omni.kit.app.get_app().post_quit(0)
except ImportError:
    pass
