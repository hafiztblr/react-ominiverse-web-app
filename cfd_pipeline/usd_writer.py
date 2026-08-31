from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from .colormap import blue_to_red
from .model import CFDField, CFDFrame


# The supplied fixture contains planar VTK_POLYGON cells. Other VTK cell types
# require explicit surface extraction/triangulation before they can become USD faces.
VTK_POLYGON = 7


def _numbers(values: Iterable, formatter=str) -> str:
    return ", ".join(formatter(value) for value in values)


def _float(value: float) -> str:
    return format(float(value), ".9g")


def _tuples(values: np.ndarray) -> str:
    return ", ".join("(" + _numbers(row, _float) + ")" for row in np.asarray(values))


def _primvar(field: CFDField) -> list[str]:
    if field.components == 1:
        usd_type = "float[]"
        payload = _numbers(np.asarray(field.values).reshape(-1), _float)
    elif field.components == 3:
        usd_type = "vector3f[]"
        payload = _tuples(np.asarray(field.values).reshape(-1, 3))
    else:
        # Preserve unusual component arrays as a flat value array plus component metadata.
        usd_type = "float[]"
        payload = _numbers(np.asarray(field.values).reshape(-1), _float)
    lines = [f"        {usd_type} primvars:{field.name} = [{payload}] (", '            interpolation = "uniform"', "        )"]
    if field.components not in (1, 3):
        lines.append(f"        custom int cfd:{field.name}:components = {field.components}")
    return lines


def _mesh_lines(frame: CFDFrame) -> list[str]:
    return [
        f"        int[] faceVertexCounts = [{_numbers(frame.mesh.face_vertex_counts, lambda x: str(int(x)))}]",
        f"        int[] faceVertexIndices = [{_numbers(frame.mesh.connectivity, lambda x: str(int(x)))}]",
        f"        point3f[] points = [{_tuples(frame.mesh.points)}]",
        f"        custom int[] cfd:cellTypes = [{_numbers(frame.mesh.cell_types, lambda x: str(int(x)))}]",
        '        uniform token subdivisionScheme = "none"',
    ]


def _validate_mesh(frame: CFDFrame) -> None:
    unsupported = sorted(set(int(value) for value in frame.mesh.cell_types) - {VTK_POLYGON})
    if unsupported:
        raise NotImplementedError(f"Unsupported VTK cell types for direct USD conversion: {unsupported}")


def _write(output: Path, lines: list[str]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join([*lines, ""]), encoding="utf-8", newline="\n")
    return output


def write_mesh_usda(frame: CFDFrame, output: str | Path) -> Path:
    """Write topology and points once for use by every frame layer."""
    _validate_mesh(frame)
    output = Path(output).resolve()
    lines = [
        "#usda 1.0", "(", '    defaultPrim = "World"', '    upAxis = "Y"', ")", "",
        'def Xform "World"', "{", '    def Scope "CFD"', "    {", '        def Mesh "Mesh" (',
        '            customData = {', '                string sourceAssociation = "VTU CellData"',
        '                string faceToCellMapping = "USD face index equals source VTK cell index"',
        "            }", "        )", "        {",
        *_mesh_lines(frame),
        "        }", "    }", "}",
    ]
    return _write(output, lines)


def write_frame_usda(
    frame: CFDFrame,
    output: str | Path,
    mesh_reference: str = "../mesh.usda",
    color_field: str = "Gas_temperature",
    time: float | None = None,
) -> Path:
    """Write time-varying fields as an override of a referenced static mesh."""
    _validate_mesh(frame)
    output = Path(output).resolve()
    if color_field not in frame.cell_fields:
        raise KeyError(f"Cell field {color_field!r} is not present")
    selected = frame.cell_fields[color_field]
    if selected.components != 1:
        raise ValueError(f"Color field {color_field!r} must be scalar")
    colors = blue_to_red(selected.values)
    lines = [
        "#usda 1.0", "(", '    defaultPrim = "World"', ")", "",
        'over "World" (', f"    references = @{mesh_reference}@</World>", ")", "{",
        '    over "CFD"', "    {", '        over "Mesh"', "        {",
        f'        custom string cfd:sourceFile = "{frame.source.name}"',
        f'        custom string cfd:colorField = "{color_field}"',
        f"        custom float cfd:colorMinimum = {_float(selected.minimum)}",
        f"        custom float cfd:colorMaximum = {_float(selected.maximum)}",
    ]
    if time is not None:
        lines.append(f"        custom double cfd:timeSeconds = {_float(time)}")
    for field in frame.cell_fields.values():
        lines.extend(_primvar(field))
    lines.extend([
        f"        color3f[] primvars:displayColor = [{_tuples(colors)}] (",
        '            interpolation = "uniform"', "        )", "        }", "    }", "}",
    ])
    return _write(output, lines)


def write_usda(frame: CFDFrame, output: str | Path, color_field: str = "Gas_temperature") -> Path:
    """Write a self-contained USD ASCII mesh for one CFD frame."""
    output = Path(output).resolve()
    _validate_mesh(frame)
    if color_field not in frame.cell_fields:
        raise KeyError(f"Cell field {color_field!r} is not present")
    selected = frame.cell_fields[color_field]
    if selected.components != 1:
        raise ValueError(f"Color field {color_field!r} must be scalar")

    colors = blue_to_red(selected.values)
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        '    upAxis = "Y"',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Scope "CFD"',
        "    {",
        '        def Mesh "Mesh" (',
        '            customData = {',
        '                string sourceAssociation = "VTU CellData"',
        '                string faceToCellMapping = "USD face index equals source VTK cell index"',
        "            }",
        "        )",
        "        {",
        *_mesh_lines(frame)[:-1],
        f'        custom string cfd:colorField = "{color_field}"',
        f"        custom float cfd:colorMinimum = {_float(selected.minimum)}",
        f"        custom float cfd:colorMaximum = {_float(selected.maximum)}",
    ]
    for field in frame.cell_fields.values():
        lines.extend(_primvar(field))
    lines.extend([
        f"        color3f[] primvars:displayColor = [{_tuples(colors)}] (",
        '            interpolation = "uniform"',
        "        )",
        '        uniform token subdivisionScheme = "none"',
        "        }",
        "    }",
        "}",
        "",
    ])
    return _write(output, lines[:-1])
