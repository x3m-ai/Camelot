# License Notice — ControlThings Suite Integration

## ctmodbus and ctserial

- **Source:** https://github.com/ControlThings-io/ctmodbus and https://github.com/ControlThings-io/ctserial
- **Author:** Justin Searle / ControlThings
- **License:** GNU Lesser General Public License v3.0 or later (LGPL-3.0-or-later)
- **Commits pinned:** ctmodbus `f8f91d9`, ctserial `58abc18`

## ctspi and cti2c

- **Source:** https://github.com/ControlThings-io/ctspi and https://github.com/ControlThings-io/cti2c
- **License:** GPL-3.0-or-later
- **Note:** Legacy Python 2 scripts requiring Bus Pirate hardware. Published as manual intelligence profiles.

## ctvelocio

- **Source:** https://github.com/ControlThings-io/ctvelocio
- **License:** GPL-3.0
- **Note:** Legacy Python 2 serial PLC assessment tool. Published as manual intelligence profile.

## Morgana runners

`morgana_ctmodbus_runner.py` and `morgana_ctserial_runner.py` are original X3M.AI works (MIT)
that wrap the ctmodbus/ctserial pymodbus/pyserial APIs for non-interactive Morgana execution.

## Important

ControlThings tools are intended for authorized security assessment of industrial control systems.
Never use against production OT/ICS systems without explicit written authorization.
Write/modify operations can alter physical process state.
