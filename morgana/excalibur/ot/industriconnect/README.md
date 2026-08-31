# IndustriConnect — Excalibur Provider (Industrial Protocols)

Morgana-native conversion of the complete IndustriAgents
[IndustriConnect](https://github.com/IndustriAgents/IndustriConnect) MCP tool
corpus. Every externally-callable MCP tool maps to one Morgana Script; runtime
values remain Tag parameters (no fake permutations).

> IndustriConnect mocks and Scripts target industrial protocols. Use them only
> in an explicitly authorized lab, simulation, or approved production exercise.
> Write/control operations preserve Morgana risk and confirmation controls.

## Source Pin

| Field | Value |
|---|---|
| Repository | https://github.com/IndustriAgents/IndustriConnect |
| Pinned commit | `aa634a12ece8186b3e6c775cea1917ea89418f5e` |
| Commit message | "Add citation section to README" |
| License | MIT (declared in each protocol `pyproject.toml`; mocks have no explicit license field) |

## Protocol Coverage (130 tools / 10 packages)

| Package | Protocol | Tools |
|---|---:|---:|
| `industriconnect-bacnet-v1` | BACnet/IP | 7 |
| `industriconnect-dnp3-v1` | DNP3 | 8 |
| `industriconnect-ethercat-v1` | EtherCAT | 14 |
| `industriconnect-ethernetip-v1` | EtherNet/IP (CIP) | 17 |
| `industriconnect-modbus-v1` | Modbus TCP/UDP/RTU | 17 |
| `industriconnect-mqtt-v1` | MQTT / Sparkplug B | 15 |
| `industriconnect-opcua-v1` | OPC UA | 7 |
| `industriconnect-profibus-v1` | PROFIBUS DP/PA | 11 |
| `industriconnect-profinet-v1` | PROFINET | 14 |
| `industriconnect-s7comm-v1` | Siemens S7 (S7comm) | 20 |

One Modbus **prompt** (`analyze_register`) is excluded: prompts are not MCP tools.

## Runtime Model

Each Script runs on the Morgana Agent `python` executor:

```
Morgana Script (python executor)
    -> import morgana_mcp_stdio_runner (SHA256-verified package asset)
    -> run_mcp_tool(command=["uv","run","<protocol>-mcp"], cwd=<runtime>/<project>/<subdir>, ...)
    -> pinned IndustriConnect MCP server (FastMCP, stdio)
    -> mock device or authorized industrial endpoint
```

The generic runner performs `initialize` -> `tools/list` -> `tools/call` over
stdin/stdout JSON-RPC, captures structured results + bounded stderr, enforces a
60 s timeout, and terminates the child cleanly.

### Runtime prerequisites (Lab Host Agent)

- Python 3.10+ and `uv` (pinned dependencies via each project's `uv.lock`)
- The pinned IndustriConnect source tree installed at the
  `ic_runtime_dir` Tag path (default `C:/ProgramData/Morgana/industriconnect`).
  Use **Industrial Lab** to install/start mock devices, or provision the tree
  manually for real-device workflows.

### Important dependency note

The upstream MCP servers use the **FastMCP v1 API** and therefore require
`mcp>=1.6,<2`. `mcp` 2.x renamed `FastMCP` to `MCPServer` and will not run the
upstream code. The pinned `uv.lock` files resolve this correctly.

## Operational Risk

| Risk | Meaning |
|---|---|
| `observe` | Read/query/discovery |
| `interact` | Protocol requests not intended to alter process state |
| `modify` | Write register/property/tag/IO, publish data, configuration |
| `disrupt` | State/CPU changes, high-impact availability operations |

Write/control tools are preserved and classified; Morgana requires explicit
operator acknowledgement for `modify`/`disrupt` content.

## Lab Integration

Every Script declares `lab_compatible: true` and a `default_port`. The
Industrial Lab **Run Compatible Scripts** action filters the Scripts view to
the matching `industriconnect-{protocol}-v1` package. Connection Tags can be
pre-filled from a running Lab Service instance's endpoint.

## Install In Morgana

1. **Scripts > Excalibur Packs > Refresh catalog**
2. Expand **IndustriConnect** and review risk badges
3. Install the required protocol packs
4. Assign required connection Tags for the authorized target (or a Lab instance)

## Update Pipeline

From `morgana/excalibur/tools`, run `update-industriconnect.ps1`. It pins the
upstream commit, syncs the runner asset, regenerates packs and the Industrial
Lab catalog, and runs static validation. Publication is manual (the script only
prints the required git commands with `-Publish`).

## Reports

- `source-inventory.json` — one record per discovered MCP tool (protocol,
  project, tool, parameters, risk, published Script ID, package)
- `conversion-report.json` — per-protocol counts + reconciliation
- `industriconnect-lab-service-inventory.json` — see Industrial Lab catalog

## Known Limitations

- Upstream mock devices are **mocks/simulators**, not hardware emulators (e.g.
  the S7 mock is not a full S7-1500; EtherCAT/PROFINET mocks use a JSON-over-TCP
  bridge rather than raw frames).
- The Modbus mock device does not start on the latest `pymodbus` 3.15 (upstream
  uses a `ModbusSequentialDataBlock` API that changed). See
  `industrial-lab/README.md` troubleshooting. This affects only the Modbus
  **mock**, not the Modbus MCP Scripts (which use the `modbus-mcp` server).
- Raw-socket protocols (EtherCAT, PROFINET) require a dedicated interface and
  Layer-2 access on the Lab Host.
