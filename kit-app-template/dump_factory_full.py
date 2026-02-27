from pxr import Usd, UsdGeom
import os

usd_path = r'c:/Users/USER/Desktop/Hafiz/Omiverse/web-app/kit-app-template/source/examples/Factory.usd'
stage = Usd.Stage.Open(usd_path)

output_file = r'c:/Users/USER/Desktop/Hafiz/Omiverse/web-app/kit-app-template/_build/windows-x86_64/release/factory_hierarchy_full.txt'

with open(output_file, 'w') as f:
    f.write(f"Detailed Hierarchy for {usd_path}\n\n")
    for prim in stage.Traverse():
        # Focus on Xformables (geometry/groups) at depths 3-6 where the interesting stuff is
        depth = len(prim.GetPath().pathString.split('/')) - 1
        if 2 <= depth <= 6:
            indent = "  " * depth
            f.write(f"{indent}{prim.GetPath()} [{prim.GetTypeName()}]\n")

print(f"Dumped detailed hierarchy to {output_file}")
