from __future__ import annotations

from pathlib import Path

import numpy as np

from .colormap import blue_to_red
from .dataset import ValidationResult
from .model import CFDField
from .usd_writer import _float, _mesh_lines, _numbers, _tuples, _validate_mesh
from .vtu_reader import read_vtu


def _usd_type(field: CFDField) -> str:
    if field.components == 1:
        return "float[]"
    if field.components == 3:
        return "vector3f[]"
    return "float[]"


def _payload(field: CFDField) -> str:
    values = np.asarray(field.values)
    if field.components == 3:
        return _tuples(values.reshape(-1, 3))
    return _numbers(values.reshape(-1), _float)


def write_animated_usda(
    validation: ValidationResult,
    output: str | Path,
    color_field: str = "Gas_temperature",
    progress=None,
) -> Path:
    """Write one animated USD with static topology and time-sampled CellData."""
    validation.require_valid()
    first = validation.first_frame
    _validate_mesh(first)
    if color_field not in first.cell_fields or first.cell_fields[color_field].components != 1:
        raise ValueError(f"Color field {color_field!r} must be scalar CellData")

    # Retaining all 201 small field frames costs far less than repeatedly parsing
    # each VTU for every field during USDA serialization.
    loaded_frames = [first]
    loaded_frames.extend(read_vtu(item.path) for item in validation.frames[1:])

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    start_time = validation.frames[0].time
    end_time = validation.frames[-1].time
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        header = [
            "#usda 1.0", "(", '    defaultPrim = "World"', '    upAxis = "Y"',
            f"    startTimeCode = {_float(start_time)}", f"    endTimeCode = {_float(end_time)}",
            "    timeCodesPerSecond = 1", "    framesPerSecond = 1", ")", "",
            'def Xform "World"', "{", '    def Scope "CFD"', "    {", '        def Mesh "Mesh" (',
            '            customData = {', '                string sourceAssociation = "VTU CellData"',
            '                string faceToCellMapping = "USD face index equals source VTK cell index"',
            '                string animationMapping = "VTU numeric suffix equals USD time code in seconds"',
            "            }", "        )", "        {", *_mesh_lines(first),
            f'        custom string cfd:colorField = "{color_field}"',
        ]
        stream.write("\n".join(header) + "\n")

        field_names = tuple(first.cell_fields)
        for field_name in field_names:
            template = first.cell_fields[field_name]
            stream.write(f"        {_usd_type(template)} primvars:{field_name} (\n")
            stream.write('            interpolation = "uniform"\n')
            stream.write("        )\n")
            stream.write(f"        {_usd_type(template)} primvars:{field_name}.timeSamples = {{\n")
            for item, frame in zip(validation.frames, loaded_frames):
                stream.write(f"            {_float(item.time)}: [{_payload(frame.cell_fields[field_name])}],\n")
            stream.write("        }\n")
            if template.components not in (1, 3):
                stream.write(f"        custom int cfd:{field_name}:components = {template.components}\n")

        stream.write("        color3f[] primvars:displayColor (\n")
        stream.write('            interpolation = "faceVarying"\n')
        stream.write("        )\n")
        stream.write("        color3f[] primvars:displayColor.timeSamples = {\n")
        for index, (item, frame) in enumerate(zip(validation.frames, loaded_frames)):
            # Per-frame scaling exposes spatial variation that a rare global
            # temperature spike would otherwise compress into one blue band.
            colors = blue_to_red(frame.cell_fields[color_field].values)
            # RTX reliably interpolates render primvars per corner. Repeating
            # each cell color for all corners preserves a sharp cell-centred
            # result while the original 700-value field stays uniform above.
            corner_colors = np.repeat(colors, frame.mesh.face_vertex_counts, axis=0)
            stream.write(f"            {_float(item.time)}: [{_tuples(corner_colors)}],\n")
            if progress:
                progress(index + 1, len(validation.frames), item)
        stream.write("        }\n")
        stream.write('        rel material:binding = </World/CFD/Looks/TemperatureMaterial>\n')
        stream.write("        }\n")
        # A front orthographic camera removes perspective tilt and tightly fits
        # the tall 1.2 x 5.6 CFD domain in the streamed viewport.
        stream.write('        def Camera "Camera"\n')
        stream.write("        {\n")
        stream.write('            token projection = "orthographic"\n')
        stream.write("            float orthographicSize = 7.2\n")
        stream.write("            float2 clippingRange = (0.1, 1000)\n")
        stream.write("            double3 xformOp:translate = (0.6, 2.8, 10)\n")
        stream.write('            uniform token[] xformOpOrder = ["xformOp:translate"]\n')
        stream.write("        }\n")
        # This plane masks bright environment backgrounds without changing the
        # CFD mesh or its cell-to-face mapping.
        stream.write('        def Mesh "Backdrop"\n')
        stream.write("        {\n")
        stream.write("            int[] faceVertexCounts = [4]\n")
        stream.write("            int[] faceVertexIndices = [0, 1, 2, 3]\n")
        stream.write("            point3f[] points = [(-5.5, -0.6, -0.1), (6.7, -0.6, -0.1), (6.7, 6.2, -0.1), (-5.5, 6.2, -0.1)]\n")
        stream.write("            color3f[] primvars:displayColor = [(0.008, 0.012, 0.02)] (\n")
        stream.write('                interpolation = "constant"\n')
        stream.write("            )\n")
        stream.write('            uniform token subdivisionScheme = "none"\n')
        stream.write('            rel material:binding = </World/CFD/Looks/BackdropMaterial>\n')
        stream.write("        }\n")
        # Use emissive PreviewSurface materials so displayColor is presented as
        # authored rather than being bleached by dome-light illumination.
        stream.write('        def Scope "Looks"\n')
        stream.write("        {\n")
        stream.write('            def Material "TemperatureMaterial"\n')
        stream.write("            {\n")
        stream.write('                token outputs:surface.connect = </World/CFD/Looks/TemperatureMaterial/Surface.outputs:surface>\n')
        stream.write('                def Shader "DisplayColorReader"\n')
        stream.write("                {\n")
        stream.write('                    uniform token info:id = "UsdPrimvarReader_float3"\n')
        stream.write('                    token inputs:varname = "displayColor"\n')
        stream.write("                    float3 outputs:result\n")
        stream.write("                }\n")
        stream.write('                def Shader "Surface"\n')
        stream.write("                {\n")
        stream.write('                    uniform token info:id = "UsdPreviewSurface"\n')
        stream.write("                    color3f inputs:diffuseColor = (0, 0, 0)\n")
        stream.write('                    color3f inputs:emissiveColor.connect = </World/CFD/Looks/TemperatureMaterial/DisplayColorReader.outputs:result>\n')
        stream.write("                    float inputs:roughness = 1\n")
        stream.write("                    token outputs:surface\n")
        stream.write("                }\n")
        stream.write("            }\n")
        stream.write('            def Material "BackdropMaterial"\n')
        stream.write("            {\n")
        stream.write('                token outputs:surface.connect = </World/CFD/Looks/BackdropMaterial/Surface.outputs:surface>\n')
        stream.write('                def Shader "Surface"\n')
        stream.write("                {\n")
        stream.write('                    uniform token info:id = "UsdPreviewSurface"\n')
        stream.write("                    color3f inputs:diffuseColor = (0.008, 0.012, 0.02)\n")
        stream.write("                    color3f inputs:emissiveColor = (0.008, 0.012, 0.02)\n")
        stream.write("                    float inputs:roughness = 1\n")
        stream.write("                    token outputs:surface\n")
        stream.write("                }\n")
        stream.write("            }\n")
        stream.write("        }\n")
        stream.write("    }\n}\n")
    return output
