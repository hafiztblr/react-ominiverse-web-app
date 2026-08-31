from __future__ import annotations

from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

from .model import CFDField, CFDFrame, CFDMesh


def _read_fields(data, association: str, expected_tuples: int) -> dict[str, CFDField]:
    fields: dict[str, CFDField] = {}
    for index in range(data.GetNumberOfArrays()):
        array = data.GetArray(index)
        if array is None or not array.GetName():
            continue
        if array.GetNumberOfTuples() != expected_tuples:
            raise ValueError(
                f"{association} array {array.GetName()!r} has {array.GetNumberOfTuples()} tuples; "
                f"expected {expected_tuples}"
            )
        values = np.array(vtk_to_numpy(array), copy=True)
        fields[array.GetName()] = CFDField(
            name=array.GetName(),
            values=values,
            association=association,
            components=array.GetNumberOfComponents(),
            vtk_type=array.GetDataTypeAsString(),
        )
    return fields


def read_vtu(path: str | Path) -> CFDFrame:
    """Read one VTU file while preserving point/cell field associations."""
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(str(source))
    reader.Update()
    if reader.GetErrorCode():
        raise ValueError(f"VTK could not read {source} (error {reader.GetErrorCode()})")
    grid = reader.GetOutput()
    if grid is None or grid.GetPoints() is None:
        raise ValueError(f"No unstructured grid points found in {source}")

    cells = grid.GetCells()
    offsets = np.array(vtk_to_numpy(cells.GetOffsetsArray()), dtype=np.int64, copy=True)
    connectivity = np.array(vtk_to_numpy(cells.GetConnectivityArray()), dtype=np.int64, copy=True)
    cell_types = np.fromiter(
        (grid.GetCellType(i) for i in range(grid.GetNumberOfCells())),
        dtype=np.uint8,
        count=grid.GetNumberOfCells(),
    )
    mesh = CFDMesh(
        points=np.array(vtk_to_numpy(grid.GetPoints().GetData()), dtype=np.float32, copy=True),
        connectivity=connectivity,
        offsets=offsets,
        cell_types=cell_types,
        bounds=tuple(float(value) for value in grid.GetBounds()),
    )
    return CFDFrame(
        source=source,
        mesh=mesh,
        point_fields=_read_fields(grid.GetPointData(), "point", mesh.point_count),
        cell_fields=_read_fields(grid.GetCellData(), "cell", mesh.cell_count),
    )
