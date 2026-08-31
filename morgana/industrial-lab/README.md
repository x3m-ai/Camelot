# Industrial Lab — Provider-Agnostic Mock/Simulator Orchestration

Industrial Lab is a first-class Morgana subsystem for deploying, managing,
resetting, observing, and destroying industrial mock devices/simulators on
Morgana Agents acting as **Lab Hosts**.

IndustriConnect is the **first** Industrial Lab provider. Industrial Lab itself
is provider-agnostic: future providers (ControlThings, ModbusPal, sim_ied,
CALDERA OT lab assets, hardware-assisted labs) are added through service
manifests and templates without changing core UI/backend.

## Architecture

```
Camelot           = content / definitions / distribution
                    (catalog.json, provider.json, services/*.json, templates/*.json)
Morgana Server    = control plane / orchestration / state
                    (LabHost, LabServiceInstance, LabInstance, LabEvent tables)
Morgana Agent     = Lab Host / execution plane
                    (actual mock/simulator processes, run via `python` executor)
Mock / Simulator  = the real process on the Agent
```

## Lab Service Manifests

Each provider ships machine-readable service manifests with:

- `service_id`, `provider`, `name`, `protocol`, `fidelity` (honest description)
- `runtime_type` (`python-process`, and extensible to `container`,
  `native-binary`, `hardware-assisted`)
- `supported_platforms`, `raw_network_required`, `container_required`
- `requirements` (with `auto_install` flag), `default_ports`
- `config_schema` (bind host, port, update interval, ...)
- `install` / `start` / `stop` / `restart` / `reset` / `health` / `logs` strategies
- `state_inspection`, `multiple_instance_support`, `presets`
- `compatible_scripts` (protocol + package for Run Compatible Scripts)

## Lifecycle States

```
discovered -> requirements_checked -> installing -> installed -> configured
  -> starting -> running -> healthy -> stopping -> stopped -> not_installed

Error states: install_failed, start_failed, unhealthy, stop_failed,
              reset_failed, uninstall_failed
```

## Happy Path

1. Deploy/select an Agent
2. **Hosts** tab → **Check** (capability probe) → **Enable**
3. **Services** tab → pick a mock → **Install**
4. Start the service (instances track `host:port`, health, logs, PID)
5. **Run Compatible Scripts** (filters Scripts to the protocol package)
6. Run a Test/Chain against the Lab endpoint
7. **Reset** / **Stop** the Lab when done

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| Host offline | Agent not beaconing; check agent service/network. Health shows `unknown` while offline. |
| Python missing | Install Python 3.10+ on the Lab Host. Check shows `python: false`. |
| uv missing | Install `uv`. Required for pinned dependency sync. Check shows `uv: false`. |
| Container runtime missing | Only required for container-type services (not the current python-process set). |
| Port collision | Industrial Lab suggests a free port; choose a custom port at install time. |
| Health failure | Verify the mock bound the configured host/port; check service logs (Logs action). |
| Raw network requirement | EtherCAT/PROFINET mocks need a dedicated NIC / Layer-2 access on the host. |
| Permission issue | Mocks bind user ports by default; privileged ports (<1024) require elevated agent. |
| Service exits immediately | Read the service log via the Logs action (bounded tail). |
| Reset failure | Some mocks use restart-with-seed; ensure the previous process fully terminated. |
| Upstream dependency error | See the protocol-specific notes below. |
| Modbus mock won't start | Upstream mock is incompatible with `pymodbus` 3.15 (`ModbusSequentialDataBlock` API change). Use an older pinned `pymodbus` (3.6.x) or a different Modbus simulator. This affects only the mock; `industriconnect-modbus-v1` Scripts use the `modbus-mcp` server, not the mock. |
| `mcp` 2.x import error | Upstream MCP servers use FastMCP v1; pin `mcp>=1.6,<2`. |

## Security

- Industrial Lab mocks are **controlled lab resources**. Reset/uninstall apply
  only to Morgana-managed instances; they never touch arbitrary external targets.
- External real devices require explicit authorization and are used through
  IndustriConnect Scripts with normal parameters, not through Lab Reset.
- Write/control Scripts preserve Morgana risk/confirmation rules.
