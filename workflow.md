# Gasifier CFD-Style USD Workflow

## Goal

Create one main `gasifier_cfd.usd` containing:

- Gasifier 3D geometry
- Separate reactor zones
- Generated 3D temperature field
- CFD-style temperature visualization
- Syngas composition visualization
- Animated syngas particle flow
- USD metadata containing telemetry values
- Animation
- Final USD ready for NVIDIA Kit / WebRTC streaming

> Important: The current telemetry data provides zone-level temperatures and outlet gas composition, not actual CFD spatial data. Therefore, the generated temperature field is a CFD-style approximation, not a real CFD solution.

---

# 1. Gasifier Geometry

Create or use the existing 3D gasifier geometry.

The reactor should be composed of separate identifiable components/zones.

Recommended USD hierarchy:

/Gasifier
    /Geometry
        /Reactor
        /GasOutlet
        /GasCooler

    /Reactor
        /DryingZone
        /PyrolysisZone
        /CombustionZone
        /ReductionZone
        /AshZone

    /TemperatureField

    /SyngasFlow
        /H2
        /CO
        /CO2
        /CH4
        /H2S

    /GasOutlet
        /Composition

---

# 2. Reactor Coordinate System

The gasifier reactor is vertically oriented.

Temperature zones from top to bottom:

Drying
    ↓
Pyrolysis
    ↓
Combustion
    ↓
Reduction
    ↓
Ash
    ↓
Gas Outlet

Determine the reactor:

- Minimum Z position
- Maximum Z position
- Reactor radius
- Height
- Zone boundaries

Map the temperature data to the corresponding Z positions.

---

# 3. Temperature Data

Use the following supplied telemetry values:

| Zone | Temperature |
|------|-------------|
| Drying | 326.3 °C |
| Pyrolysis | 565.1 °C |
| Combustion | 875.0 °C |
| Reduction | 707.2 °C |
| Ash | 390.6 °C |
| Gas Outlet | 316.1 °C |

The combustion zone at 875.0 °C must be the hottest region.

---

# 4. Generate a 3D Temperature Field

The supplied data represents:

    T(z)

Generate an approximate spatial field:

    T(x, y, z)

Create a 3D grid/field covering the reactor.

Example resolution:

    X = 40 cells
    Y = 40 cells
    Z = 120 cells

Each cell should have an interpolated temperature value.

Interpolate smoothly between the six supplied zone temperatures rather than creating six hard color bands.

---

# 5. Add Radial Temperature Variation

The temperature should not be identical across the entire reactor cross-section.

Introduce a small radial variation so that the field has natural 3D variation.

The combustion zone should contain a hotter central region.

Conceptually:

    T(x,y,z)
      =
    T_zone(z)
      +
    radial_variation(x,y)

Do not introduce unrealistic extreme variations.

The purpose is to create a visually convincing CFD-style field while remaining based on the supplied telemetry.

---

# 6. CFD-Style Temperature Visualization

Convert the generated temperature field into a visual temperature representation.

Use a continuous temperature gradient rather than obvious individual colored spheres/dots.

Suggested conceptual mapping:

    Low temperature
        ↓
    Blue
        ↓
    Cyan
        ↓
    Green
        ↓
    Yellow
        ↓
    Orange
        ↓
    Red
        ↓
    High temperature

The field should appear continuous and integrated with the reactor.

The result should visually resemble a CFD temperature contour/volume visualization.

Avoid making the visualization look like:

    ● ● ● ● ●
    ● ● ● ● ●
    ● ● ● ● ●

Individual visible spheres/dots should not dominate the visualization.

---

# 7. Combustion Zone

The combustion zone is the hottest region.

Temperature:

    875.0 °C

Make this region visually prominent.

It should have a concentrated hot area rather than simply being a flat horizontal colored band.

The surrounding areas should smoothly transition toward lower temperatures.

---

# 8. Syngas Composition

At the gas outlet, use:

    H2  = 25.80%
    CO  = 18.84%
    CO2 = 5.77%
    CH4  = 3.32%
    H2S  = 0.27%
    O2  = 0.00%

These values represent outlet composition.

Do NOT treat them as spatial concentration data throughout the reactor because spatial composition data was not supplied.

---

# 9. Syngas Flow Visualization

Create a syngas flow visualization from the reactor toward:

    Reduction Zone
          ↓
    Gas Outlet
          ↓
    Gas Cooler

Use animated particles to represent the gas flow.

Particles should move continuously toward the outlet.

The particle distribution can approximately represent the supplied outlet composition.

For example, per 1000 particles:

    H2  ≈ 258
    CO  ≈ 188
    CO2 ≈ 58
    CH4  ≈ 33
    H2S  ≈ 3
    O2  = 0

This is a visualization approximation.

---

# 10. USD Metadata

Store the original telemetry values as USD attributes.

Example:

/Gasifier/Reactor/DryingZone

    temperature = 326.3
    temperatureUnit = "C"

 /Gasifier/Reactor/PyrolysisZone

    temperature = 565.1

 /Gasifier/Reactor/CombustionZone

    temperature = 875.0

 /Gasifier/Reactor/ReductionZone

    temperature = 707.2

 /Gasifier/Reactor/AshZone

    temperature = 390.6

 /Gasifier/GasOutlet

    temperature = 316.1

    H2 = 25.80
    CO = 18.84
    CO2 = 5.77
    CH4 = 3.32
    H2S = 0.27
    O2 = 0.0

The USD should therefore contain both visualization and process metadata.

---

# 11. Animation

Implement two types of animation.

## Temperature Animation

The temperature visualization should be capable of changing when telemetry values change.

Example:

    Combustion:
    875 °C
       ↓
    890 °C
       ↓
    910 °C

The temperature field/material should update accordingly.

## Syngas Animation

Gas particles should continuously move through:

    Reactor
       ↓
    Combustion
       ↓
    Reduction
       ↓
    Gas Outlet
       ↓
    Gas Cooler

---

# 12. Final USD Structure

The final scene should be contained in ONE main USD:

    gasifier_cfd.usd

Conceptual structure:

/Gasifier

    /Geometry
        /Reactor
        /GasOutlet
        /GasCooler

    /Reactor
        /DryingZone
        /PyrolysisZone
        /CombustionZone
        /ReductionZone
        /AshZone

    /TemperatureField
        /Field
        /Material

    /SyngasFlow
        /H2
        /CO
        /CO2
        /CH4
        /H2S

    /GasOutlet
        /Composition

    /Metadata

---

# 13. Implementation Phases

## Phase 1 — Geometry

Create or import the gasifier geometry.

Output:

    gasifier geometry inside USD

---

## Phase 2 — Temperature Field

Input:

    326.3
    565.1
    875.0
    707.2
    390.6
    316.1

Process:

    Zone temperatures
          ↓
    Z-axis mapping
          ↓
    Interpolation
          ↓
    3D temperature field
          ↓
    CFD-style visualization

---

## Phase 3 — Syngas

Input:

    H2
    CO
    CO2
    CH4
    H2S
    O2

Process:

    Outlet composition
          ↓
    Particle distribution
          ↓
    Animated syngas flow

---

## Phase 4 — USD Composition

Combine:

    Geometry
        +
    Temperature field
        +
    Syngas visualization
        +
    Animation
        +
    Metadata

Output:

    gasifier_cfd.usd

---

## Phase 5 — Streaming

The final USD should be usable with the existing NVIDIA/Omniverse workflow:

    gasifier_cfd.usd
          ↓
    NVIDIA Kit
          ↓
    WebRTC
          ↓
    USD Viewer
          ↓
    Web Application

---

# 14. Important Constraints

1. Keep everything in ONE main `gasifier_cfd.usd`.

2. Do not create fake CFD measurements and present them as real CFD data.

3. The generated 3D temperature field is an approximation derived from zone-level temperatures.

4. Outlet gas composition must not be interpreted as a full spatial concentration field.

5. Preserve the separate reactor zones.

6. Avoid visible uniform sphere/dot patterns for the temperature field.

7. The combustion zone must remain the hottest region.

8. Temperature transitions should be smooth.

9. Preserve existing USD/VTU/Omniverse functionality in the project.

10. Reuse existing project utilities wherever possible.

11. Keep the USD structure modular internally even though the final deliverable is one USD.

12. Verify the generated USD by loading it in the existing viewer/Omniverse pipeline.