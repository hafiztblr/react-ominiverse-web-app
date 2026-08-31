# Implement VTU → USD CFD Visualization Pipeline

I need you to implement a CFD visualization pipeline for my existing application.

## Context

My application already has a USD viewer based on NVIDIA Omniverse/Kit and streams the rendered result to a React web viewer using WebRTC.

The new use case is a dedicated CFD viewer.

The CFD simulation output is provided as approximately 200 `.vtu` files, with one file representing one second of simulation time.

Example:

```text
ENTIRE_DOMAIN_0001.vtu
ENTIRE_DOMAIN_0002.vtu
ENTIRE_DOMAIN_0003.vtu
...
ENTIRE_DOMAIN_0200.vtu
```

Therefore the files represent approximately:

```text
0001 → t = 0 s
0002 → t = 1 s
0003 → t = 2 s
...
0200 → t = 199 s
```

I have provided one real sample VTU file named:

```text
ENTIRE_DOMAIN_0010.vtu
```

Use this real VTU structure as the source of truth. Do not invent the CFD field names or topology.

The sample contains approximately:

* 781 points
* 700 cells
* CellData fields
* Gas velocity
* Solids velocity
* Gas temperature
* Solids temperature
* Pressure
* Gas/solids properties
* Multiple gas species mass fractions
* Multiple solids mass fractions

Important: the CFD fields are primarily CELL DATA, not point data.

---

# Overall objective

Build a conversion pipeline:

```text
VTU files
   ↓
VTU parser
   ↓
CFD dataset representation
   ↓
USD
   ↓
NVIDIA Kit
   ↓
WebRTC
   ↓
Existing React USD viewer
```

The first version should focus ONLY on:

1. Reading VTU files.
2. Reading the unstructured mesh.
3. Preserving cell topology.
4. Reading CellData.
5. Creating USD geometry.
6. Preserving CFD fields as USD attributes.
7. Visualizing Gas_temperature as a color field.
8. Supporting multiple time steps.

Do NOT implement NanoVDB/OpenVDB yet.
Do NOT implement volume rendering yet.
Do NOT implement streamlines yet.
Do NOT implement a real CFD solver.

We are only implementing VTU → USD visualization.

---

# Phase 1 — Inspect the VTU

Before writing the converter, inspect the supplied sample VTU.

Determine:

* Number of points.
* Number of cells.
* Cell types.
* Connectivity.
* Offsets.
* Point coordinates.
* All PointData arrays.
* All CellData arrays.
* Data types.
* Array dimensions.
* Vector fields.
* Scalar fields.
* Whether the VTU is ASCII, binary, or compressed.
* Whether the mesh uses mixed cell types.

Print a report similar to:

```text
VTU FILE
-----------------------------
Points: 781
Cells: 700

Cell types:
  tetra: ...
  hexahedron: ...
  wedge: ...
  ...

CellData:
  EP_G
  P_G
  Gas_Velocity
  Solids_Velocity_1
  Solids_Velocity_2
  Gas_temperature
  Solids_temperature_1
  Solids_temperature_2
  ...
```

Do not assume that all VTU files have identical topology until this has been verified.

---

# Phase 2 — Check the 200-frame dataset

Create a dataset loader that accepts a directory:

```text
cfd_data/
    ENTIRE_DOMAIN_0001.vtu
    ENTIRE_DOMAIN_0002.vtu
    ...
    ENTIRE_DOMAIN_0200.vtu
```

Sort files numerically, not lexicographically.

Create a validation step:

```text
Frame 0001
Frame 0002
...
Frame 0200
```

For every frame verify:

* Point count.
* Cell count.
* Cell types.
* Connectivity/topology.
* Bounding box.

If the mesh topology is identical between frames, store the mesh only once.

If topology changes, detect that and report it clearly.

Do not silently assume identical topology.

---

# Phase 3 — Create an internal CFD data model

Create a clean internal representation.

Conceptually:

```text
CFDDataset
{
    mesh:
    {
        points
        cells
        cellTypes
        bounds
    }

    frames:
    [
        {
            time: 0,
            fields:
            {
                Gas_temperature,
                P_G,
                Gas_Velocity,
                ...
            }
        },

        {
            time: 1,
            fields:
            {
                Gas_temperature,
                P_G,
                Gas_Velocity,
                ...
            }
        }
    ]
}
```

Separate:

```text
static mesh
```

from:

```text
time-varying fields
```

This is important because the mesh may be identical for all 200 frames.

---

# Phase 4 — Correctly handle CellData

The actual VTU uses CellData.

Do NOT incorrectly treat cell values as vertex values.

For example:

```text
Cell 0
    Gas_temperature = 850 K

Cell 1
    Gas_temperature = 852 K

Cell 2
    Gas_temperature = 861 K
```

These values belong to cells.

Preserve the association.

Create metadata describing:

```text
field name
field type
association = cell
component count
units if available
min
max
```

For example:

```text
Gas_temperature
    type: scalar
    association: cell
    units: K
    min: ...
    max: ...

Gas_Velocity
    type: vector
    association: cell
    components: 3
    units: m/s
```

Do not invent units if they are not present in the source file.

---

# Phase 5 — Convert VTU topology to USD

Create a USD writer.

Use:

```text
UsdGeomMesh
```

for the first implementation.

The USD scene should have a structure similar to:

```text
/World
    /CFD
        /Mesh
```

The mesh should represent the actual unstructured CFD mesh.

IMPORTANT:

VTU supports multiple cell types.

Implement conversion for the cell types actually found in the supplied VTU.

Do not blindly convert every possible VTK cell type unless necessary.

Correctly translate:

```text
VTK connectivity
+
VTK cell type
```

into:

```text
USD mesh topology
```

If a VTK cell type cannot be represented directly by USD Mesh, triangulate or otherwise convert it appropriately while preserving the visible geometry.

Document any topology conversion.

---

# Phase 6 — Store CFD fields in USD

Preserve the CFD fields as USD primvars/custom attributes.

For example:

```text
primvars:Gas_temperature
primvars:P_G
primvars:Gas_Velocity
primvars:Solids_Velocity_1
...
```

Because the source is CellData, use the appropriate USD interpolation/association strategy.

Do not incorrectly label cell data as vertex data.

If USD cannot directly represent the source association in the desired way, create a well-documented representation that preserves the original cell values and their mapping to cells.

The generated USD must retain enough information to reconstruct the original CFD field.

---

# Phase 7 — First visualization: Gas_temperature

The first visible CFD visualization should be:

```text
Gas_temperature
       ↓
normalize min/max
       ↓
colormap
       ↓
USD displayColor
```

Use a blue → cyan → green → yellow → red gradient.

The temperature should visually vary across the CFD domain.

Do not create a fake temperature field.

Use the actual values from the VTU.

Because the source data is cell-centered, map the cell temperature correctly to the generated visualization geometry.

If necessary, duplicate/expand cell vertices so each cell can have its own color.

---

# Phase 8 — Time series

Support all 200 VTU files.

The desired logical structure is:

```text
CFD Dataset
│
├── Mesh
│
└── Time
    ├── t=0
    ├── t=1
    ├── t=2
    ...
    └── t=199
```

The user should eventually be able to select:

```text
Frame: 1 / 200
Time: 10 seconds
```

and see the corresponding Gas_temperature field.

For the first implementation, it is acceptable to generate:

```text
frame_0001.usda
frame_0002.usda
...
```

if a single animated USD is unnecessarily complicated.

However, design the converter so that the static mesh is not duplicated unnecessarily.

Preferred architecture:

```text
CFD/
    mesh.usd

    frames/
        frame_0001.usd
        frame_0002.usd
        ...
```

or another efficient USD structure that references one static mesh and changes only field data.

Do not create 200 complete duplicate meshes if the topology is unchanged.

---

# Phase 9 — Output metadata

Generate a metadata file:

```text
cfd_dataset.json
```

Example structure:

```json
{
  "frameCount": 200,
  "timeStart": 0,
  "timeEnd": 199,
  "timeStep": 1,
  "mesh": {
    "points": 781,
    "cells": 700
  },
  "fields": [
    {
      "name": "Gas_temperature",
      "type": "scalar",
      "association": "cell"
    },
    {
      "name": "Gas_Velocity",
      "type": "vector",
      "association": "cell"
    },
    {
      "name": "P_G",
      "type": "scalar",
      "association": "cell"
    }
  ]
}
```

Only include values actually present in the source data.

---

# Phase 10 — CLI

Create a command-line converter.

Something like:

```bash
python convert_vtu_to_usd.py \
    --input ./cfd_data \
    --output ./cfd_usd
```

Optional:

```bash
--field Gas_temperature
```

Optional:

```bash
--start 1
--end 200
```

Optional:

```bash
--validate-only
```

For example:

```bash
python convert_vtu_to_usd.py \
    --input ./cfd_data \
    --output ./cfd_usd \
    --field Gas_temperature
```

The converter should print:

```text
Scanning VTU files...

Found: 200 frames

Validating mesh...
✓ topology consistent
✓ point count consistent
✓ cell count consistent

Reading fields...
✓ Gas_temperature
✓ Gas_Velocity
✓ P_G
...

Generating USD...

✓ mesh.usd
✓ frame_0001.usd
✓ frame_0002.usd
...
✓ frame_0200.usd

Generating metadata...
✓ cfd_dataset.json

Done.
```

---

# Phase 11 — Viewer integration

Do not rewrite the existing USD viewer.

Integrate the generated CFD USD into the existing Kit streaming pipeline.

The existing flow is approximately:

```text
React
   ↓
openStageRequest
   ↓
Kit
   ↓
USD stage
   ↓
WebRTC
   ↓
React viewer
```

The CFD application should load:

```text
cfd_usd/mesh.usd
```

and the appropriate field/time data.

Initially, only display:

```text
Gas_temperature
```

with the temperature colormap.

---

# Phase 12 — React UI

Only after the USD rendering works, add a minimal CFD UI:

```text
CFD

Field
[ Gas Temperature ▼ ]

Frame
[ 1 / 200 ]

Time
[ 0 sec ]

Temperature
Min: xxx K
Max: xxx K

Colormap
[ Blue → Red ]
```

For now, do not implement all fields in the UI.

Start with:

```text
Gas_temperature
```

Once this works, we will add:

```text
P_G
Gas_Velocity
Solids_temperature_1
Solids_temperature_2
species
```

---

# Phase 13 — Testing

Create automated/basic tests for:

### Test 1

Load one VTU.

Verify:

```text
781 points
700 cells
```

or the actual values found in the file.

### Test 2

Verify all CellData arrays are discovered.

### Test 3

Verify `Gas_temperature` length equals the number of cells.

### Test 4

Verify `Gas_Velocity` has 3 components per cell.

### Test 5

Convert one VTU → USD.

### Test 6

Open generated USD in a USD viewer.

### Test 7

Verify temperature colors are visible.

### Test 8

Process all 200 frames.

### Test 9

Verify topology is not duplicated unnecessarily.

---

# Very important implementation constraints

1. Use the REAL VTU structure supplied with this project.
2. Do not invent CFD field names.
3. Do not invent CFD values.
4. Do not convert CellData into PointData without explicitly explaining the mapping.
5. Preserve cell-centered data.
6. Separate static mesh from time-varying fields.
7. Do not implement NanoVDB yet.
8. Do not implement OpenVDB yet.
9. Do not implement volume rendering yet.
10. Do not implement streamlines yet.
11. Do not implement a CFD solver.
12. Do not replace the existing USD/WebRTC architecture.
13. Keep the converter modular so we can later add VDB/volume rendering.
14. Use the actual uploaded `ENTIRE_DOMAIN_0010.vtu` as the initial test fixture.
15. Before making large changes, inspect the existing repository structure and identify the current USD/Kit integration points.

---

# Expected final architecture

The implementation should eventually look like:

```text
                 CFD SOLVER
                     │
                     ▼
               200 × .vtu
                     │
                     ▼
             VTU Parser/Loader
                     │
                     ▼
              CFD Data Model
                     │
          ┌──────────┴──────────┐
          │                     │
      Static Mesh          Time Fields
          │                     │
          │          ┌──────────┼──────────┐
          │          │          │          │
          │      Temperature  Pressure  Velocity
          │          │          │          │
          └──────────┴──────────┴──────────┘
                     │
                     ▼
                  USD Writer
                     │
                     ▼
               CFD USD Dataset
                     │
                     ▼
                NVIDIA Kit
                     │
                  WebRTC
                     │
                     ▼
                React Viewer
```

## Deliverables

Implement the code, not just an explanation.

At the end provide:

1. Files created/modified.
2. Directory structure.
3. Installation commands.
4. Conversion command.
5. How to load the generated USD into the existing Kit application.
6. How the time-step selection works.
7. How `Gas_temperature` is mapped to colors.
8. Any limitations discovered with the actual VTU cell types.
9. A short explanation of how the implementation can later be extended to NanoVDB/volume rendering.

Before coding, inspect the existing project and the supplied VTU and make implementation decisions based on the actual repository and actual VTU structure.
