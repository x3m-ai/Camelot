# ControlThings Suite — ICS/IIoT Industrial Protocol Assessment

**Provider:** ControlThings (Justin Searle)  
**Website:** https://www.controlthings.io/  
**Scripts:** 33 | **Packages:** 5 | **Chains:** 0  
**License:** LGPL-3.0-or-later (ctmodbus/ctserial) / GPL-3.0 (ctspi/cti2c/ctvelocio)  

---

## What is ControlThings?

ControlThings is a suite of open-source tools for industrial protocol and embedded hardware security assessment, created by Justin Searle. It provides protocol primitives for Modbus, serial devices, SPI/I2C embedded hardware, and vendor-specific PLCs.

---

## Packages

| Package | Scripts | Component | Risk |
|---|---|---|---|
| `controlthings-modbus-read-v1` | 17 | ctmodbus | interact |
| `controlthings-modbus-write-v1` | 8 | ctmodbus | modify |
| `controlthings-serial-v1` | 2 | ctserial | modify |
| `controlthings-embedded-v1` | 4 | ctspi + cti2c | interact/modify |
| `controlthings-velocio-v1` | 2 | ctvelocio | interact/modify |

---

## Components

| Component | Role | Transport | Hardware |
|---|---|---|---|
| ctmodbus | Executable — Modbus TCP/UDP/RTU/ASCII | IP network + serial | None for TCP/UDP |
| ctserial | Executable — raw serial | Serial | Serial adapter |
| ctspi | Manual profile — SPI EEPROM/flash | SPI | Bus Pirate adapter |
| cti2c | Manual profile — I2C EEPROM | I2C | Bus Pirate adapter |
| ctvelocio | Manual profile — Velocio PLC | Serial | Velocio PLC + serial |

---

## Prerequisites

- **Linux/macOS Morgana Agent** with Python 3.8+
- `pip install ctmodbus ctserial` on the Agent
- For Modbus TCP/UDP: network access to authorized OT target
- For RTU/ASCII/Serial: serial adapter (/dev/ttyUSB0 or equivalent)
- For SPI/I2C: Bus Pirate adapter (manual profiles only)
- **Authorized isolated OT/ICS lab** — never use against production systems

---

## Risk model

| Operation | Risk | Notes |
|---|---|---|
| Read coils/registers/device ID | interact | Read-only |
| Send serial hex/text | modify | Can alter device state |
| Write register/coil | modify | Alters device state — confirm target |
| SPI/I2C write or erase | modify | Alters chip contents |

---

## Excluded repositories

| Repository | Reason |
|---|---|
| ctlib-hart | Library only — no CLI entrypoint |
| ctip / ctrf | Placeholder repositories — no source |
| ctui | UI library dependency |
| ctbin | Binary analysis tool — out of scope |
| ControlThingsPlatform | Linux distribution reference |
| modbuspal / sim_ied | Simulators for lab use |

See [LICENSE-NOTICE.md](LICENSE-NOTICE.md) for attribution.
