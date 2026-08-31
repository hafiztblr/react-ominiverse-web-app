from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

import numpy as np

from .model import CFDFrame
from .vtu_reader import read_vtu


_FRAME_NUMBER = re.compile(r"(\d+)$")


@dataclass(frozen=True)
class FrameFile:
    path: Path
    number: int
    time: float


@dataclass(frozen=True)
class ValidationResult:
    frames: tuple[FrameFile, ...]
    first_frame: CFDFrame
    topology_consistent: bool
    errors: tuple[str, ...]

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError("Dataset validation failed:\n" + "\n".join(self.errors))


def frame_number(path: Path) -> int:
    match = _FRAME_NUMBER.search(path.stem)
    if not match:
        raise ValueError(f"VTU filename has no trailing frame number: {path.name}")
    return int(match.group(1))


def discover_frames(directory: str | Path, start: int | None = None, end: int | None = None) -> tuple[FrameFile, ...]:
    directory = Path(directory).resolve()
    found = sorted(directory.glob("*.vtu"), key=frame_number)
    frames = tuple(
        FrameFile(path=path, number=frame_number(path), time=float(frame_number(path)))
        for path in found
        if (start is None or frame_number(path) >= start) and (end is None or frame_number(path) <= end)
    )
    if not frames:
        raise FileNotFoundError(f"No VTU frames found in {directory}")
    numbers = [item.number for item in frames]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Duplicate numeric frame suffixes found")
    return frames


def _digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _field_schema(frame: CFDFrame) -> tuple[tuple[str, str, int, str], ...]:
    fields = (*frame.point_fields.values(), *frame.cell_fields.values())
    return tuple((field.name, field.association, field.components, field.vtk_type) for field in fields)


def validate_dataset(
    directory: str | Path,
    start: int | None = None,
    end: int | None = None,
    progress=None,
) -> ValidationResult:
    frames = discover_frames(directory, start, end)
    first = read_vtu(frames[0].path)
    base_topology = _digest(first.mesh.connectivity, first.mesh.offsets, first.mesh.cell_types)
    base_points = _digest(first.mesh.points)
    base_schema = _field_schema(first)
    errors: list[str] = []

    for index, item in enumerate(frames):
        frame = first if index == 0 else read_vtu(item.path)
        prefix = f"Frame {item.number:04d}"
        if frame.mesh.point_count != first.mesh.point_count:
            errors.append(f"{prefix}: point count {frame.mesh.point_count}, expected {first.mesh.point_count}")
        if frame.mesh.cell_count != first.mesh.cell_count:
            errors.append(f"{prefix}: cell count {frame.mesh.cell_count}, expected {first.mesh.cell_count}")
        if _digest(frame.mesh.connectivity, frame.mesh.offsets, frame.mesh.cell_types) != base_topology:
            errors.append(f"{prefix}: cell topology differs")
        if _digest(frame.mesh.points) != base_points:
            errors.append(f"{prefix}: point coordinates differ")
        if not np.allclose(frame.mesh.bounds, first.mesh.bounds, rtol=0.0, atol=1e-7):
            errors.append(f"{prefix}: bounds {frame.mesh.bounds} differ from {first.mesh.bounds}")
        if _field_schema(frame) != base_schema:
            errors.append(f"{prefix}: field schema differs")
        if progress:
            progress(index + 1, len(frames), item)

    return ValidationResult(
        frames=frames,
        first_frame=first,
        topology_consistent=not any("topology differs" in error or "point coordinates differ" in error for error in errors),
        errors=tuple(errors),
    )
