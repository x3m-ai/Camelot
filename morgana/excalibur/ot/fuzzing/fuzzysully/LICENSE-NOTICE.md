# License Notice — ANSSI FuzzySully Integration

## FuzzySully

- **Source:** https://github.com/ANSSI-FR/fuzzysully
- **Author:** Quarkslab / ANSSI-FR contributors
- **License:** GNU Lesser General Public License v2.1 (LGPL-2.1)
- **Version integrated:** 0.1.1
- **Commit pinned:** 50a0631178331d2cc39b6ed554b9b68050580f92

This Morgana integration uses FuzzySully unmodified via its Python API.
The source is not bundled in this repository; the runtime wrapper
(`morgana_fuzzysully_runner.py`) invokes the FuzzySully package installed
on the Linux Morgana Agent's Python environment.

## Fuzzowski (included within FuzzySully)

FuzzySully is built on a modified version of [Fuzzowski](https://github.com/nccgroup/fuzzowski)
by NCC Group. License: GPL-2.0.

## opcua-asyncio (enhanced version included within FuzzySully)

FuzzySully includes an enhanced fork of [opcua-asyncio](https://github.com/FreeOpcUa/opcua-asyncio).
License: LGPL-2.1.

## Fuzzing knowledge acknowledgments

The FuzzySully project acknowledges fuzzing contributions and techniques from:
- Claroty Research
- Fraunhofer / BSI-derived OPC UA fuzzing research

## Morgana wrapper

`morgana_fuzzysully_runner.py` is an original X3M.AI work (MIT license)
that wraps the FuzzySully Python API for non-interactive Morgana execution.

## Distribution note

The `morgana_fuzzysully_runner.py` wrapper is published under MIT.
The FuzzySully package itself must be installed separately on the Linux Agent
and remains subject to LGPL-2.1. No FuzzySully source or modified binaries
are bundled in this Camelot asset directory.
