# Changelog

All notable releases and updates for the X3M.AI ecosystem are documented here.

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
