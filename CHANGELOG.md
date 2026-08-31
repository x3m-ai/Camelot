# Changelog

All notable releases and updates for the X3M.AI ecosystem are documented here.

## Morgana / Camelot — IndustriConnect provider + Industrial Lab (August 2026)

### Added
- Complete IndustriConnect Excalibur provider (IndustriAgents/IndustriConnect @ `aa634a12`, MIT)
  - 130 MCP tools mapped one-to-one to Morgana Scripts across 10 protocol packages
  - Generic MCP stdio runner (`morgana_mcp_stdio_runner`) shipped as a SHA256-verified package asset
  - Full source reconciliation (`source-inventory.json`, `conversion-report.json`)
- New provider-agnostic **Industrial Lab** subsystem in Morgana
  - Sidebar page after Agents with Overview / Services / Labs / Hosts tabs
  - Lab Host capability checks, service lifecycle (install/configure/start/stop/restart/reset/uninstall), health, logs
  - Multiple instances, port collision detection, provider-native reset
  - 10 IndustriConnect mock service manifests + 4 Lab templates
- Backend: `industrial_lab` models, router (`/api/v2/industrial-lab`), orchestrator
- Docs: provider guide (`morgana/excalibur/ot/industriconnect/README.md`), Lab guide (`morgana/industrial-lab/README.md`)
- Update pipeline: `update-industriconnect.ps1`

### Notes
- Industrial Lab is provider-agnostic; IndustriConnect is the first provider.
- Mock devices run on Morgana Agents (Lab Hosts); Morgana Server remains the control plane; Camelot the distribution plane.

## Morgana / Camelot — MEDUSA provider (August 2026)

### Added
- Complete dedicated MEDUSA mobile instrumentation provider (Ch0pin/medusa @ `8c62447d`, GPL-3.0)
- 147 Scripts (133 Android/iOS modules + 14 standalone snippets) across 38 platform×category packages
- Source-faithful MEDUSA compiler reusing the existing Morgana Frida executor
- MEDUSA module Options exposed as Morgana runtime tag parameters
- Full source reconciliation, static validation, and package/catalog metadata
- Provider documentation (`morgana/excalibur/mobile/medusa/README.md`) and license notice

### Notes
- MEDUSA is intentionally independent from the Frida Mobile provider; overlapping functionality is preserved across both providers.

## Merlino v1.4.0 (February 2026)

### Added
- Cloudflare Pages deployment
- Cloudflare Worker licensing system
- License activation flow (OTP via email)
- Cloud sync for settings
- STIX/Intune large file CDN optimization
- Settings UI redesign (Cloud sync section)

### Integrations
- MITRE ATT&CK Enterprise, Mobile, ICS, Azure
- Microsoft Sentinel, Defender for Office 365, Intune
- Caldera/Morgana Arsenal (Red Team)
- MISP (IOC management)
- OpenAI, Mistral (AI analysis)
- NIST NVD (CVE enrichment)
- Exploit-DB (46,000+ exploits)

---

*For detailed release history, see individual product repositories.*
