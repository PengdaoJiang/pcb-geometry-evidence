# PCB geometry evidence

Read-only Gerber / ODB feature geometry and comparison tools extracted from a working board-design evidence pipeline. This repository contains the complete portable geometry subsystem, with original synthetic inputs and regression cases; it is not a vendor board package or a CAD application.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python compare.py examples/reference.gbr examples/changed.gbr
```

## What the code actually handles

- Ordered dark/clear Gerber composition, macro rotation, legacy modal-operation state and explicitly bounded arc approximation.
- ODB feature symbols, orientations, polygons and polarity, with unsupported shapes rejected rather than guessed.
- Directed coverage and tiled exact differences that retain thin missing features. Comparison tolerance is reported separately from parser approximation.
- Primitive identity checks preserve order across polarity boundaries and preserve duplicates.
- IPC pin fields, drill glyph/stroke encodings and document-curve evidence kernels.

`compare.py` binds both source hashes and reports missing/extra area. It never auto-aligns, repairs a source file or edits a PCB. The two example layers intentionally differ by a short track segment. `tests/` covers independent geometry constructions, empty inputs, negative polarity, rotations, legacy arcs and thin-feature counterexamples.

## Scope

Native schematic/layout extraction, vendor libraries, proprietary design archives, machine-specific CAD launchers and company design parameters are not distributed. These kernels are a portable subsystem of that larger toolchain. A geometric match is not electrical correctness, DRC clearance or manufacturing approval; the code makes those boundaries explicit in its results.

Dependencies: Gerbonara (Apache-2.0), Shapely (BSD-3-Clause); installed separately. The implementation here retains its own repository license.
