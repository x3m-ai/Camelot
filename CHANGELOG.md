# Changelog

All notable releases and updates for the X3M.AI ecosystem are documented here.

## Morgana / Camelot — Drozer provider (August 2026)

### Added
- Complete dedicated **Drozer** Android application-security provider
  - 79 source-faithful Scripts (65 core + 14 external) across 8 namespace packages (app, auxiliary, exploit, information, post, scanner, shell, tools)
  - Three separately pinned upstreams: [ReversecLabs/drozer](https://github.com/ReversecLabs/drozer) @ `d992f637` (v3.2.0, BSD-3-Clause), `drozer-agent` @ `c1f18ceb` (BSD-3-Clause), [drozer-modules](https://github.com/ReversecLabs/drozer-modules) @ `c6fb1570`
  - AST-based module discovery, argument extraction, risk model, and Mobile ATT&CK mapping
  - Generic `morgana_drozer_runner.py` asset (`executor=python`) over the pinned isolated Drozer runtime (`drozer console connect` over `adb forward tcp:31415`)
  - Mobile Lab Drozer readiness / agent check / prepare operations + `drozer_readiness` device state
  - `Android Drozer Lab` and `Android AppSec Lab` Mobile Lab templates
- Backend: `build_drozer_command` in `core/mobile_lab.py`, `drozer_readiness` column + migration, router op-map, `DROZER - ` Script prefix
- Camelot content: `morgana/excalibur/mobile/drozer/` (8 packs + runtime + inventory/report), catalog + classification, `update-drozer.ps1` pipeline
- Docs: 10 `DROZER_*.md` guides in Morgana + `mobile/drozer/README.md` in Camelot

### Notes
- Drozer is intentionally independent from MEDUSA and Frida Mobile (zero cross-provider suppression).
- Android-only; Apple Simulator / iOS is explicitly NOT_SUPPORTED.
- 23 core candidates are manual/support/internal (reported, never silently dropped); full reconciliation has zero silent loss.
- Live Android runtime E2E is NOT RUN where no emulator/system image is available (reported accurately, never false PASS).

## Morgana / Camelot — Mobile Lab subsystem (August 2026)

### Added
- New provider-agnostic **Mobile Lab** subsystem in Morgana (adjacent to Industrial Lab)
  - Sidebar page after Industrial Lab with Overview / Devices / Apps / Templates / Hosts tabs
  - Provider registry: Android Emulator, Apple Simulator, Physical Android, Physical iOS, Corellium (external API architecture)
  - Ownership model (`MORGANA_MANAGED` / `DISCOVERED_EXTERNAL` / `EXTERNAL_PHYSICAL` / `EXTERNAL_API_MANAGED`) gating destructive lifecycle actions
  - Runtime / readiness / connection / reservation state machines + structured error model
  - Android SDK-root-aware host detection, AVD lifecycle, snapshots, APK install/launch/logs/screenshot, Frida readiness
  - Apple Simulator via `xcrun simctl` (macOS/Xcode only; no false Windows/Linux support)
  - `MobileAppAsset` (SHA-256, package/bundle ID, license status) + `MobileLabTemplate` / `MobileLabInstance`
  - Stable `mobilelab://<device>/app/<app>` target references
  - Frida/MEDUSA binding via `Run Compatible Scripts` (existing Frida executor reused — no duplicate runtime)
- Backend: `mobile_lab` models, `core/mobile_lab.py`, router (`/api/v2/mobile-lab`), 4 test files
- Camelot content: `morgana/mobile-lab/catalog.json` (5 providers + 4 templates) + community guide
- Docs: 13 `MOBILE_LAB_*.md` guides in the Morgana repo

### Notes
- Apple Simulator is macOS/Xcode only. Physical devices are non-destructive by default.
- MEDUSA and Frida Mobile remain independent Script providers dynamically bound to Mobile Lab targets.
- Full AVD boot, iOS Simulator, physical-device and Corellium runtime tests are NOT RUN where the environment/credentials are unavailable (reported accurately, never false PASS).

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
