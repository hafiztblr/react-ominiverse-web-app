from __future__ import annotations

import argparse
from pathlib import Path

import vtk

from cfd_pipeline import convert_dataset, read_vtu, validate_dataset, write_animated_usda, write_usda


def _report(frame) -> None:
    print("VTU FILE")
    print("-----------------------------")
    print(f"File: {frame.source}")
    print(f"Points: {frame.mesh.point_count}")
    print(f"Cells: {frame.mesh.cell_count}")
    print(f"Bounds: {frame.mesh.bounds}")
    print("Cell types:")
    for cell_type in sorted(set(int(value) for value in frame.mesh.cell_types)):
        count = int((frame.mesh.cell_types == cell_type).sum())
        print(f"  {cell_type} ({vtk.vtkCellTypes.GetClassNameFromTypeId(cell_type)}): {count}")
    print("PointData:")
    for field in frame.point_fields.values():
        print(f"  {field.name}: {field.vtk_type}, components={field.components}, tuples={len(field.values)}")
    if not frame.point_fields:
        print("  (none)")
    print("CellData:")
    for field in frame.cell_fields.values():
        print(
            f"  {field.name}: {field.vtk_type}, components={field.components}, "
            f"tuples={len(field.values)}, min={field.minimum:.9g}, max={field.maximum:.9g}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect, validate, and convert VTU CFD data to USD ASCII")
    parser.add_argument("--input", required=True, help="Input .vtu file or directory")
    parser.add_argument("--output", help="Output .usda file or dataset directory")
    parser.add_argument("--field", default="Gas_temperature", help="Scalar CellData field used for displayColor")
    parser.add_argument("--start", type=int, help="First numeric frame suffix, inclusive")
    parser.add_argument("--end", type=int, help="Last numeric frame suffix, inclusive")
    parser.add_argument("--inspect", action="store_true", help="Print the real VTU structure")
    parser.add_argument("--validate-only", action="store_true", help="Validate a directory without writing USD")
    parser.add_argument("--animated", action="store_true", help="Write all selected frames into one time-sampled USDA")
    args = parser.parse_args()

    source = Path(args.input)
    if source.is_file():
        frame = read_vtu(source)
        if args.inspect:
            _report(frame)
        if args.validate_only:
            print("Validation passed.")
            return 0
        if not args.output:
            parser.error("--output is required for conversion")
        result = write_usda(frame, args.output, args.field)
        field = frame.cell_fields[args.field]
        print(f"Color field {args.field}: {field.minimum:.9g} to {field.maximum:.9g}")
        print(f"Wrote {result}")
        return 0

    if not source.is_dir():
        parser.error(f"input does not exist: {source}")
    print("Scanning and validating VTU files...")
    def validation_progress(done, total, item):
        if done == 1 or done == total or done % 25 == 0:
            print(f"  validated {done}/{total}: Frame {item.number:04d}")
    validation = validate_dataset(source, args.start, args.end, validation_progress)
    validation.require_valid()
    print(f"Found: {len(validation.frames)} frames")
    print("Topology, points, bounds, counts, and field schema are consistent.")
    if args.inspect:
        _report(validation.first_frame)
    if args.validate_only:
        print("Validation passed; no files written.")
        return 0
    if not args.output:
        parser.error("--output is required for conversion")
    if args.animated:
        print("Generating one animated USD...")
        def animation_progress(done, total, item):
            if done == 1 or done == total or done % 25 == 0:
                print(f"  authored {done}/{total}: time {item.time:g} s")
        animated = write_animated_usda(validation, args.output, args.field, animation_progress)
        print(f"Wrote animated stage {animated}")
        return 0
    print("Generating USD...")
    def conversion_progress(done, total, item):
        if done == 1 or done == total or done % 25 == 0:
            print(f"  wrote {done}/{total}: frame_{item.number:04d}.usda")
    metadata = convert_dataset(source, args.output, args.field, args.start, args.end, validation, conversion_progress)
    print(f"Wrote mesh.usda and {len(validation.frames)} frame layers")
    print(f"Wrote {metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
