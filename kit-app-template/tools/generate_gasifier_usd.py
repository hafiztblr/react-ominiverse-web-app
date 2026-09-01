"""Generate the self-contained gasifier CFD-style OpenUSD stage.

The field is a deterministic telemetry interpolation, not a CFD solver result.
No third-party Python modules are required; Kit/OpenUSD can open the generated
ASCII layer directly even though its extension is ``.usd``.
"""

from __future__ import annotations

import argparse
import colorsys
import math
import re
from pathlib import Path


ZONE_SAMPLES = [
    ("DryingZone", 9.6, 12.0, 326.3),
    ("PyrolysisZone", 7.2, 9.6, 565.1),
    ("CombustionZone", 4.8, 7.2, 875.0),
    ("ReductionZone", 2.6, 4.8, 707.2),
    ("AshZone", 0.4, 2.6, 390.6),
]
PROFILE = [(0.15, 316.1), (1.5, 390.6), (3.7, 707.2), (6.0, 875.0), (8.4, 565.1), (10.8, 326.3)]
COMPOSITION = [("H2", 25.80, (0.25, 0.75, 1.0)), ("CO", 18.84, (1.0, 0.55, 0.12)),
               ("CO2", 5.77, (0.55, 0.75, 0.45)), ("CH4", 3.32, (0.72, 0.35, 1.0)),
               ("H2S", 0.27, (1.0, 0.92, 0.15)), ("O2", 0.0, (0.35, 0.55, 1.0))]

TEMPERATURE_KEYS = {
    "reactor_dryingZoneTemperatureC": "DryingZone",
    "reactor_pyrolysisZoneTemperatureC": "PyrolysisZone",
    "reactor_combustionZoneTemperatureC": "CombustionZone",
    "reactor_reductionZoneTemperatureC": "ReductionZone",
    "reactor_ashZoneTemperatureC": "AshZone",
    "reactor_gasOutletTemperatureC": "Outlet",
}
COMPOSITION_KEYS = {
    "gasCooler_H2VolPercentage": "H2", "gasCooler_COVolPercentage": "CO",
    "gasCooler_CO2VolPercentage": "CO2", "gasCooler_CH4VolPercentage": "CH4",
    "gasCooler_H2SVolPercentage": "H2S", "gasCooler_O2VolPercentage": "O2",
}


def parse_sample_data(path: Path):
    """Parse the named telemetry fields; comments/units after values are allowed."""
    text = path.read_text(encoding="utf-8", errors="replace")
    expected = (*TEMPERATURE_KEYS, *COMPOSITION_KEYS)
    found = {}
    for key in expected:
        match = re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(key)}(?:\s*\([^)]*\))?\s*:\s*(-?\d+(?:\.\d+)?)",
            text,
        )
        if match:
            found[key] = float(match.group(1))
    missing = [key for key in (*TEMPERATURE_KEYS, *COMPOSITION_KEYS) if key not in found]
    if missing:
        raise ValueError(f"Missing required telemetry fields in {path}: {', '.join(missing)}")
    temperatures = {zone: found[key] for key, zone in TEMPERATURE_KEYS.items()}
    composition = {species: found[key] for key, species in COMPOSITION_KEYS.items()}
    if any(not 0.0 <= value <= 100.0 for value in composition.values()):
        raise ValueError("Syngas volume percentages must be between 0 and 100")
    return temperatures, composition


def data_model(input_path: Path | None = None):
    if input_path is None:
        temperatures = {name: temp for name, _, _, temp in ZONE_SAMPLES}
        temperatures["Outlet"] = PROFILE[0][1]
        composition_values = {species: pct for species, pct, _ in COMPOSITION}
    else:
        temperatures, composition_values = parse_sample_data(input_path)
    zone_samples = [(name, z0, z1, temperatures[name]) for name, z0, z1, _ in ZONE_SAMPLES]
    profile = [(0.15, temperatures["Outlet"]), (1.5, temperatures["AshZone"]),
               (3.7, temperatures["ReductionZone"]), (6.0, temperatures["CombustionZone"]),
               (8.4, temperatures["PyrolysisZone"]), (10.8, temperatures["DryingZone"])]
    colors = {species: rgb for species, _, rgb in COMPOSITION}
    composition = [(species, composition_values[species], colors[species]) for species, _, _ in COMPOSITION]
    return zone_samples, profile, composition, temperatures


def fmt(value: float) -> str:
    return f"{value:.5f}".rstrip("0").rstrip(".")


def vec(values) -> str:
    return "[" + ", ".join(f"({fmt(x)}, {fmt(y)}, {fmt(z)})" for x, y, z in values) + "]"


def arr(values) -> str:
    return "[" + ", ".join(fmt(v) for v in values) + "]"


def int_arr(values) -> str:
    return "[" + ", ".join(str(v) for v in values) + "]"


def axial_temperature(z: float, profile=PROFILE) -> float:
    for (z0, t0), (z1, t1) in zip(profile, profile[1:]):
        if z <= z1:
            u = max(0.0, (z - z0) / (z1 - z0))
            # Smoothstep removes visible derivative breaks at telemetry stations.
            u = u * u * (3.0 - 2.0 * u)
            return t0 + (t1 - t0) * u
    return profile[-1][1]


def field_temperature(x: float, y: float, z: float, profile=PROFILE) -> float:
    # Supplied values define the centerline. The wall is moderately cooler,
    # particularly around combustion, while a small deterministic azimuthal
    # term avoids perfect horizontal/radial bands. The maximum remains 875 C.
    radius = min(1.0, math.hypot(x, y) / 1.62)
    combustion_weight = math.exp(-((z - 6.0) / 1.75) ** 2)
    wall_loss = radius ** 1.65 * (13.0 + 46.0 * combustion_weight)
    theta = math.atan2(y, x)
    asymmetry = radius * (2.5 + 5.5 * combustion_weight) * (0.5 + 0.5 * math.sin(2.0 * theta + 0.7 * z))
    lower, upper = min(t for _, t in profile), max(t for _, t in profile)
    return max(lower, min(upper, axial_temperature(z, profile) - wall_loss - asymmetry))


def color(temp: float, minimum=316.1, maximum=875.0) -> tuple[float, float, float]:
    span = max(1e-6, maximum - minimum)
    u = max(0.0, min(1.0, (temp - minimum) / span))
    return colorsys.hsv_to_rgb((1.0 - u) * 0.67, 0.92, 1.0)


def material(name: str, rgb, opacity=1.0, metallic=0.0) -> str:
    return f'''        def Material "{name}"
        {{
            token outputs:surface.connect = </Gasifier/Looks/{name}/Shader.outputs:surface>
            def Shader "Shader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({fmt(rgb[0])}, {fmt(rgb[1])}, {fmt(rgb[2])})
                float inputs:metallic = {fmt(metallic)}
                float inputs:roughness = 0.32
                float inputs:opacity = {fmt(opacity)}
                token outputs:surface
            }}
        }}
'''


def temperature_material() -> str:
    """PreviewSurface that explicitly consumes the field's displayColor primvar."""
    return '''        def Material "TemperatureMaterial"
        {
            token outputs:surface.connect = </Gasifier/Looks/TemperatureMaterial/Shader.outputs:surface>
            def Shader "DisplayColorReader"
            {
                uniform token info:id = "UsdPrimvarReader_float3"
                token inputs:varname = "displayColor"
                float3 outputs:result
            }
            def Shader "Shader"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </Gasifier/Looks/TemperatureMaterial/DisplayColorReader.outputs:result>
                float inputs:roughness = 0.72
                float inputs:opacity = 0.92
                token outputs:surface
            }
        }
'''


def cylinder(name, z, height, radius, material_path, opacity=None, extra="", x=0.0, y=0.0) -> str:
    opacity_line = f"\n            float primvars:displayOpacity = {fmt(opacity)}" if opacity is not None else ""
    xform_order = '["xformOp:rotateXYZ", "xformOp:translate"]' if "xformOp:rotateXYZ" in extra else '["xformOp:translate"]'
    return f'''        def Cylinder "{name}"
        {{
            uniform token axis = "Z"
            double radius = {fmt(radius)}
            double height = {fmt(height)}
            double3 xformOp:translate = ({fmt(x)}, {fmt(y)}, {fmt(z)})
            uniform token[] xformOpOrder = {xform_order}
            rel material:binding = <{material_path}>{opacity_line}{extra}
        }}
'''


def cone(name, z, height, bottom_radius, top_radius, material_path, opacity=None, x=0.0, y=0.0) -> str:
    opacity_line = f"\n            float primvars:displayOpacity = {fmt(opacity)}" if opacity is not None else ""
    return f'''        def Cone "{name}"
        {{
            uniform token axis = "Z"
            double radius = {fmt(bottom_radius)}
            double height = {fmt(height)}
            double3 xformOp:scale = (1, 1, 1)
            double3 xformOp:translate = ({fmt(x)}, {fmt(y)}, {fmt(z)})
            uniform token[] xformOpOrder = ["xformOp:scale", "xformOp:translate"]
            rel material:binding = <{material_path}>{opacity_line}
            custom double geometry:topRadius = {fmt(top_radius)}
        }}
'''


def torus_mesh(name: str, z: float, major: float, minor: float, material_path: str, x=0.0) -> str:
    points, counts, indices = [], [], []
    nu, nv = 48, 10
    for iu in range(nu):
        u = 2 * math.pi * iu / nu
        for iv in range(nv):
            v = 2 * math.pi * iv / nv
            rr = major + minor * math.cos(v)
            points.append((x + rr * math.cos(u), rr * math.sin(u), z + minor * math.sin(v)))
    for iu in range(nu):
        for iv in range(nv):
            a = iu * nv + iv
            b = ((iu + 1) % nu) * nv + iv
            c = ((iu + 1) % nu) * nv + (iv + 1) % nv
            d = iu * nv + (iv + 1) % nv
            counts.append(4); indices.extend((a, b, c, d))
    return f'''        def Mesh "{name}"
        {{
            point3f[] points = {vec(points)}
            int[] faceVertexCounts = {int_arr(counts)}
            int[] faceVertexIndices = {int_arr(indices)}
            uniform token subdivisionScheme = "none"
            rel material:binding = <{material_path}>
        }}
'''


def pipe_curve(name: str, points, diameter: float, material_path: str) -> str:
    return f'''        def BasisCurves "{name}"
        {{
            uniform token type = "linear"
            uniform token basis = "bezier"
            uniform token wrap = "nonperiodic"
            int[] curveVertexCounts = [{len(points)}]
            point3f[] points = {vec(points)}
            float[] widths = [{fmt(diameter)}]
            uniform token widths:interpolation = "constant"
            rel material:binding = <{material_path}>
        }}
'''


FLOW_ANCHORS = (
    (0.00, (0.0, 0.0, 11.25)),  # Drying at top
    (0.18, (0.0, 0.0, 8.40)),   # Pyrolysis
    (0.38, (0.0, 0.0, 6.00)),   # Combustion hot core
    (0.58, (0.0, 0.0, 3.70)),   # Reduction
    (0.72, (0.0, 0.0, 1.45)),   # Ash / gas outlet region
    (0.78, (2.05, 0.0, 1.35)),  # lower side outlet
    (0.86, (4.60, 0.0, 1.35)),  # horizontal transfer pipe
    (0.94, (5.35, 0.0, 4.65)),  # rising pipe into cooler
    (1.00, (7.00, 0.0, 4.65)),  # gas cooler inlet
)


def particle_path(progress: float, lane_angle: float = 0.0, lane_radius: float = 0.0):
    """Return a particle position in /Gasifier local coordinates.

    Reactor geometry, zones, and SyngasFlow are siblings below /Gasifier and
    therefore share this coordinate space. Offsets rotate from the reactor XY
    cross-section into the outlet YZ cross-section after the elbow.
    """
    progress = max(0.0, min(1.0, progress))
    for (p0, a), (p1, b) in zip(FLOW_ANCHORS, FLOW_ANCHORS[1:]):
        if progress <= p1:
            u = (progress - p0) / (p1 - p0)
            u = max(0.0, min(1.0, u))
            u = u * u * (3.0 - 2.0 * u)
            center = tuple(a[j] + (b[j] - a[j]) * u for j in range(3))
            break
    else:
        center = FLOW_ANCHORS[-1][1]

    radial = lane_radius * (0.72 + 0.28 * math.sin(4.0 * math.pi * progress + lane_angle))
    if progress < 0.74:
        # Vertical reactor: local cross-section is XY. Fade lanes into the bend.
        fade = 1.0 if progress <= 0.68 else max(0.0, (0.74 - progress) / 0.06)
        return (center[0] + radial * math.cos(lane_angle) * fade,
                center[1] + radial * math.sin(lane_angle) * fade,
                center[2])
    # Transfer pipe: offsets use its local YZ cross-section through both bends.
    outlet_radius = min(0.11, radial)
    return (center[0], center[1] + outlet_radius * math.cos(lane_angle),
            center[2] + outlet_radius * math.sin(lane_angle))


def generate(output: Path, input_path: Path | None = None) -> dict[str, int]:
    zone_samples, profile, composition, temperatures = data_model(input_path)
    temp_min, temp_max = min(t for _, t in profile), max(t for _, t in profile)
    # Concentric translucent contour shells create a continuous volumetric
    # appearance without point sprites or an external OpenVDB dependency.
    field_pos, field_temp, field_colors, field_opacity = [], [], [], []
    face_counts, face_indices = [], []
    radial_shells = (0.24, 0.52, 0.82, 1.12, 1.42, 1.72)
    ntheta, nz = 40, 61
    for shell_index, nominal_radius in enumerate(radial_shells):
        shell_start = len(field_pos)
        for iz in range(nz):
            z = 0.18 + iz * 11.55 / (nz - 1)
            for ia in range(ntheta):
                theta = 2.0 * math.pi * ia / ntheta
                # Gentle coherent deformation makes contours organic while
                # keeping every surface safely inside the reactor wall.
                radius = nominal_radius * (1.0 + 0.018 * math.sin(3.0 * theta + 0.55 * z))
                x, y = radius * math.cos(theta), radius * math.sin(theta)
                t = field_temperature(x, y, z, profile)
                field_pos.append((x, y, z))
                field_temp.append(t)
                field_colors.append(color(t, temp_min, temp_max))
                # Inner hot contours must dominate; cool outer contours remain
                # translucent so they cannot mask the combustion core.
                field_opacity.append(0.38 - 0.05 * shell_index)
        for iz in range(nz - 1):
            for ia in range(ntheta):
                nxt = (ia + 1) % ntheta
                a = shell_start + iz * ntheta + ia
                b = shell_start + iz * ntheta + nxt
                c = shell_start + (iz + 1) * ntheta + nxt
                d = shell_start + (iz + 1) * ntheta + ia
                face_counts.append(4)
                face_indices.extend((a, b, c, d))

    # Metadata describes the conceptual sampling lattice; visualization is a
    # continuous contour representation rather than one sphere per sample.
    nx = ny = 40

    looks = (material("Steel", (0.14, 0.17, 0.20), 1.0, 0.88)
             + material("ShellGlass", (0.08, 0.18, 0.24), 0.025)
             + temperature_material())
    for species, _, rgb in composition:
        looks += material(species + "Material", rgb, 0.9)

    zones = ""
    zone_colors = [(0.1, .45, 1), (0, .9, .65), (1, .16, .02), (1, .62, .05), (.2, .55, 1)]
    for (name, z0, z1, temp), rgb in zip(zone_samples, zone_colors):
        looks += material(name + "Material", rgb, 0.045)
        extra = f'''\n            token visibility = "invisible"\n            custom double telemetry:temperature = {temp}\n            custom string telemetry:temperatureUnit = "C"\n            custom string process:zoneName = "{name}"'''
        zones += cylinder(name, (z0 + z1) / 2, z1 - z0 - .04, 1.88, f"/Gasifier/Looks/{name}Material", .045, extra)

    particle_blocks = ""
    particle_total = 0
    particle_times = tuple(range(0, 97, 8))
    for si, (species, pct, _) in enumerate(composition):
        count = round(pct * 2) if pct else 0
        particle_total += count
        time_positions = {time: [] for time in particle_times}
        for i in range(count):
            angle = 2.0 * math.pi * ((i * 0.61803398875 + si * 0.137) % 1.0)
            radius = 0.10 + 0.34 * ((i * 37 % 101) / 100.0)
            stagger = (i % 7) * 0.0025
            for time in particle_times:
                progress = min(1.0, time / 96.0 + stagger)
                time_positions[time].append(particle_path(progress, angle, radius))
        samples = ", ".join(f"{time}: {vec(time_positions[time])}" for time in particle_times)
        particle_blocks += f'''        def Points "{species}"
        {{
            custom double composition:percent = {fmt(pct)}
            custom string composition:basis = "measured outlet volume percent"
            custom string flow:coordinateSpace = "/Gasifier local space (shared with reactor geometry)"
            custom string flow:path = "Drying -> Pyrolysis -> Combustion -> Reduction -> GasOutlet -> GasCooler"
            point3f[] points.timeSamples = {{ {samples} }}
            float[] widths = [{", ".join(["0.105"] * count)}]
            color3f[] primvars:displayColor = [({fmt(composition[si][2][0])}, {fmt(composition[si][2][1])}, {fmt(composition[si][2][2])})]
            uniform token primvars:displayColor:interpolation = "constant"
            rel material:binding = </Gasifier/Looks/{species}Material>
        }}
'''

    flange_geometry = "".join(torus_mesh(f"Flange_{i:02d}", z, 2.12, 0.105, "/Gasifier/Looks/Steel")
                                for i, z in enumerate((0.35, 2.6, 4.8, 7.2, 9.6, 11.95)))
    support_geometry = "".join(
        cylinder(f"VerticalTie_{i:02d}", 6.15, 11.3, 0.045, "/Gasifier/Looks/Steel",
                 x=2.03 * math.cos(2 * math.pi * i / 8), y=2.03 * math.sin(2 * math.pi * i / 8))
        for i in range(8)
    )
    outlet_centerline = [(1.85, 0, 1.35), (2.4, 0, 1.35), (3.5, 0, 1.35), (4.6, 0, 1.35),
                         (5.05, 0, 1.65), (5.25, 0, 2.35), (5.35, 0, 3.35), (5.35, 0, 4.65),
                         (6.05, 0, 4.65), (7.0, 0, 4.65)]
    usd = f'''#usda 1.0
(
    defaultPrim = "Gasifier"
    upAxis = "Z"
    metersPerUnit = 1
    timeCodesPerSecond = 24
    startTimeCode = 0
    endTimeCode = 96
    customLayerData = {{
        string project = "Gasifier CFD-style digital twin"
        string fieldProvenance = "Interpolated telemetry visualization; not CFD solver output"
    }}
)

def Xform "Gasifier" (
    kind = "assembly"
)
{{
    custom string documentation = "Self-contained gasifier geometry, telemetry-derived temperature field, and animated outlet syngas"
    custom string data:temperatureUnit = "C"
    custom string data:compositionUnit = "volume percent"
    custom string data:source = "{input_path.name if input_path else 'built-in defaults'}"
    custom string data:fieldClassification = "CFD-style approximation from zone telemetry; not solver CFD"
    def Scope "Looks"
    {{
{looks}    }}
    def Xform "Geometry"
    {{
{cylinder("ReactorShell", 6.15, 11.7, 2.0, "/Gasifier/Looks/ShellGlass", .025)}{cylinder("TopHead", 12.08, .36, 2.16, "/Gasifier/Looks/Steel")}{cylinder("TopNozzle", 12.48, .62, .58, "/Gasifier/Looks/Steel")}{cone("AshHopper", -.45, 1.65, 1.75, 0.42, "/Gasifier/Looks/ShellGlass", .04)}{cylinder("BottomNozzle", -1.38, .55, .44, "/Gasifier/Looks/Steel")}{flange_geometry}{support_geometry}{pipe_curve("GasOutlet", outlet_centerline, .52, "/Gasifier/Looks/Steel")}{cylinder("GasCooler", 2.9, 4.7, 1.02, "/Gasifier/Looks/ShellGlass", .035, x=7.0)}{cylinder("CoolerTopHead", 5.32, .32, 1.16, "/Gasifier/Looks/Steel", x=7.0)}{cylinder("CoolerBottomHead", .48, .32, 1.16, "/Gasifier/Looks/Steel", x=7.0)}{torus_mesh("CoolerTopFlange", 5.18, 1.08, .085, "/Gasifier/Looks/Steel", x=7.0)}{torus_mesh("CoolerBottomFlange", .62, 1.08, .085, "/Gasifier/Looks/Steel", x=7.0)}
    }}
    def Scope "Reactor"
    {{
{zones}    }}
    def Scope "TemperatureField"
    {{
        def Mesh "Field"
        {{
            custom string field:type = "interpolated3DScalar"
            custom int3 field:gridResolution = ({nx}, {ny}, {nz})
            custom string field:interpolation = "smoothstep axial interpolation with radial wall cooling and deterministic azimuthal variation"
            custom string field:visualization = "nested translucent continuous contour shells; approximate CFD-style field"
            custom float[] field:temperature = {arr(field_temp)}
            custom string field:temperatureUnit = "C"
            point3f[] points = {vec(field_pos)}
            int[] faceVertexCounts = {int_arr(face_counts)}
            int[] faceVertexIndices = {int_arr(face_indices)}
            uniform token subdivisionScheme = "none"
            uniform bool doubleSided = true
            color3f[] primvars:displayColor = {vec(field_colors)}
            uniform token primvars:displayColor:interpolation = "vertex"
            float[] primvars:displayOpacity = {arr(field_opacity)}
            uniform token primvars:displayOpacity:interpolation = "vertex"
            rel material:binding = </Gasifier/Looks/TemperatureMaterial>
        }}
    }}
    def Scope "SyngasFlow"
    {{
{particle_blocks}    }}
    def Xform "GasOutlet"
    {{
        custom double telemetry:temperature = {fmt(temperatures['Outlet'])}
        custom string telemetry:temperatureUnit = "C"
        custom double composition:H2 = {fmt(dict((s, p) for s, p, _ in composition)['H2'])}
        custom double composition:CO = {fmt(dict((s, p) for s, p, _ in composition)['CO'])}
        custom double composition:CO2 = {fmt(dict((s, p) for s, p, _ in composition)['CO2'])}
        custom double composition:CH4 = {fmt(dict((s, p) for s, p, _ in composition)['CH4'])}
        custom double composition:H2S = {fmt(dict((s, p) for s, p, _ in composition)['H2S'])}
        custom double composition:O2 = {fmt(dict((s, p) for s, p, _ in composition)['O2'])}
    }}
    def DomeLight "EnvironmentLight"
    {{
        float intensity = 700
        float exposure = 0.5
        color3f color = (0.72, 0.82, 1)
    }}
    def Camera "OverviewCamera"
    {{
        double3 xformOp:translate = (22, -27, 13)
        double3 xformOp:rotateXYZ = (70, 0, 40)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
        float focalLength = 48
    }}
}}
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(usd, encoding="utf-8", newline="\n")
    return {"field_points": len(field_pos), "particles": particle_total}


def main() -> None:
    default = Path(__file__).resolve().parents[1] / "source" / "examples" / "gasifier_cfd.usd"
    default_input = Path(__file__).resolve().parents[2] / "samle-data.txt"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=default)
    parser.add_argument("--input", type=Path, default=default_input, help="Named gasifier telemetry text file")
    args = parser.parse_args()
    counts = generate(args.output.resolve(), args.input.resolve())
    print(f"Generated {args.output.resolve()} ({counts['field_points']} field vertices, {counts['particles']} particles)")


if __name__ == "__main__":
    main()
