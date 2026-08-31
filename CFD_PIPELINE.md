# VTU to USD CFD pipeline

The converter reads VTK unstructured grids without changing PointData/CellData
association. The supplied dataset is a planar grid of `VTK_POLYGON` cells, so
each VTK cell maps directly to one USD mesh face. CellData is authored as USD
`uniform` primvars: one value per face. USD face index `N` maps to VTU cell `N`.

## Install

```powershell
python -m pip install -r requirements-cfd.txt
```

## Inspect and validate

```powershell
python convert_vtu_to_usd.py --input .\vtu-files\ENTIRE_DOMAIN_0010.vtu --inspect --validate-only
python convert_vtu_to_usd.py --input .\vtu-files --validate-only
```

## Convert

Single self-contained layer:

```powershell
python convert_vtu_to_usd.py --input .\vtu-files\ENTIRE_DOMAIN_0010.vtu --output .\single.usda
```

Shared-mesh time series:

```powershell
python convert_vtu_to_usd.py --input .\vtu-files --output .\cfd_usd --field Gas_temperature
```

One animated USD containing all time samples:

```powershell
python convert_vtu_to_usd.py --input .\vtu-files --output .\cfd_usd\cfd_animation.usda --field Gas_temperature --animated
```

The animated stage stores topology once and authors every CellData primvar plus
`displayColor` at time codes 0 through 200. `timeCodesPerSecond = 1`, matching
the numeric VTU suffix to simulation seconds. Temperature colors are normalized
per frame to expose spatial CFD variation despite rare dataset-wide outliers.
Original fields remain 700-value `uniform` cell primvars. For RTX rendering,
each cell color is repeated at its four corners as a 2800-value `faceVarying`
`displayColor`, producing sharp per-cell CFD bands without averaging neighbors.

The dataset output contains `mesh.usda`, `cfd_dataset.json`, and one frame layer
under `frames/`. Each frame references `mesh.usda`; topology and points are not
duplicated. Open a frame layer (for example `cfd_usd/frames/frame_0010.usda`) in
Kit. The existing React application can send that path using its existing
`openStageRequest` flow. Selecting another time step initially means opening its
corresponding frame layer.

`Gas_temperature` is normalized using the selected frame's actual minimum and
maximum and mapped through blue, cyan, green, yellow, and red. No values or units
are synthesized. The real files contain no unit metadata, so metadata does not
claim Kelvin even though the field name/use case describes temperature.

## Current topology limitation

Only VTK cell type 7 (`VTK_POLYGON`) is accepted because it is the only type in
all supplied files. A future 3D dataset will need a surface-extraction policy for
volume cells before authoring `UsdGeomMesh`. The parser/data model can later feed
a NanoVDB/OpenVDB writer without changing VTU discovery or field association.
