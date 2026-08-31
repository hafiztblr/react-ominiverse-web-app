from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class CFDMesh:
    points: NDArray[np.floating]
    connectivity: NDArray[np.integer]
    offsets: NDArray[np.integer]
    cell_types: NDArray[np.integer]
    bounds: tuple[float, float, float, float, float, float]

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def cell_count(self) -> int:
        return len(self.cell_types)

    @property
    def face_vertex_counts(self) -> NDArray[np.integer]:
        return np.diff(self.offsets)


@dataclass(frozen=True)
class CFDField:
    name: str
    values: NDArray[np.floating]
    association: str
    components: int
    vtk_type: str
    units: str | None = None

    @property
    def kind(self) -> str:
        return "scalar" if self.components == 1 else "vector" if self.components == 3 else "array"

    @property
    def minimum(self) -> float:
        return float(np.min(self.values))

    @property
    def maximum(self) -> float:
        return float(np.max(self.values))


@dataclass(frozen=True)
class CFDFrame:
    source: Path
    mesh: CFDMesh
    point_fields: dict[str, CFDField]
    cell_fields: dict[str, CFDField]

