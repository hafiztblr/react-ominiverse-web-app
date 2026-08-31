from __future__ import annotations

import json
from pathlib import Path

from .dataset import ValidationResult, validate_dataset
from .vtu_reader import read_vtu
from .usd_writer import write_frame_usda, write_mesh_usda


def _metadata(validation: ValidationResult, field_ranges: dict[str, list[float]], color_field: str) -> dict:
    first = validation.first_frame
    frames = validation.frames
    fields = []
    for field in (*first.point_fields.values(), *first.cell_fields.values()):
        item = {
            "name": field.name,
            "type": field.kind,
            "association": field.association,
            "components": field.components,
            "dataType": field.vtk_type,
            "minimum": field_ranges[field.name][0],
            "maximum": field_ranges[field.name][1],
        }
        if field.units is not None:
            item["units"] = field.units
        fields.append(item)
    times = [item.time for item in frames]
    steps = [b - a for a, b in zip(times, times[1:])]
    time_step = steps[0] if steps and all(step == steps[0] for step in steps) else None
    return {
        "frameCount": len(frames),
        "timeStart": times[0],
        "timeEnd": times[-1],
        "timeStep": time_step,
        "colorField": color_field,
        "mesh": {
            "file": "mesh.usda",
            "points": first.mesh.point_count,
            "cells": first.mesh.cell_count,
            "bounds": list(first.mesh.bounds),
            "vtkCellTypes": sorted(set(int(value) for value in first.mesh.cell_types)),
            "topologyShared": validation.topology_consistent,
        },
        "frames": [
            {"number": item.number, "time": item.time, "file": f"frames/frame_{item.number:04d}.usda", "source": item.path.name}
            for item in frames
        ],
        "fields": fields,
    }


def convert_dataset(
    input_directory: str | Path,
    output_directory: str | Path,
    color_field: str = "Gas_temperature",
    start: int | None = None,
    end: int | None = None,
    validation: ValidationResult | None = None,
    progress=None,
) -> Path:
    validation = validation or validate_dataset(input_directory, start, end)
    validation.require_valid()
    output = Path(output_directory).resolve()
    write_mesh_usda(validation.first_frame, output / "mesh.usda")
    field_ranges: dict[str, list[float]] = {
        field.name: [field.minimum, field.maximum]
        for field in (*validation.first_frame.point_fields.values(), *validation.first_frame.cell_fields.values())
    }
    for index, item in enumerate(validation.frames):
        frame = validation.first_frame if index == 0 else read_vtu(item.path)
        for field in (*frame.point_fields.values(), *frame.cell_fields.values()):
            field_ranges[field.name][0] = min(field_ranges[field.name][0], field.minimum)
            field_ranges[field.name][1] = max(field_ranges[field.name][1], field.maximum)
        write_frame_usda(
            frame,
            output / "frames" / f"frame_{item.number:04d}.usda",
            color_field=color_field,
            time=item.time,
        )
        if progress:
            progress(index + 1, len(validation.frames), item)
    metadata_path = output / "cfd_dataset.json"
    metadata_path.write_text(
        json.dumps(_metadata(validation, field_ranges, color_field), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return metadata_path
