# Morgana Mobile Lab — Community Guide

Mobile Lab is Morgana's provider-agnostic subsystem for provisioning and
managing mobile security test environments: Android emulators, Apple iOS
Simulators, physical devices, and future external virtual-device providers.

## Content Plane (this repository)

| Path | Purpose |
|---|---|
| `catalog.json` | Provider metadata + template index fetched by Morgana on demand |
| `templates/*.json` | Declarative `MobileLabTemplate` environments |

## Providers

| Provider | Type | Platforms | Host requirement |
|---|---|---|---|
| `android-emulator` | LOCAL_HOST_PROVIDER | android | Android SDK + adb + emulator + virtualization |
| `apple-simulator` | LOCAL_HOST_PROVIDER | ios | macOS + Xcode + simctl |
| `physical-android` | PHYSICAL_DEVICE_PROVIDER | android | adb |
| `physical-ios` | PHYSICAL_DEVICE_PROVIDER | ios | macOS |
| `corellium` | EXTERNAL_API_PROVIDER | android, ios | API credentials |

Apple Simulator is macOS/Xcode only. Physical devices are non-destructive by
default. Corellium requires a valid account; the architecture is validated but
runtime is not run without credentials.

## Templates

| Template | Platform | Provider | Baseline |
|---|---|---|---|
| `android-clean-avd` | android | android-emulator | wipe |
| `android-app-test-lab` | android | android-emulator | snapshot |
| `ios-simulator-app-lab` | ios | apple-simulator | erase |
| `physical-android-test-session` | android | physical-android | none |
| `android-drozer-lab` | android | android-emulator | wipe (drozer runtime + agent) |
| `android-appsec-lab` | android | android-emulator | wipe (drozer + frida + MEDUSA) |
| `android-mastg-playground-lab` | android | android-emulator | wipe (drozer + frida + MASTG apps) |
| `ios-mastg-playground-lab` | ios | apple-simulator | erase (MASTG iOS JWT app; macOS/Xcode Host required) |

## Drozer integration

Drozer (ReversecLabs/drozer + drozer-agent + drozer-modules) integrates as an
Android tooling capability on Mobile Lab targets. Its Excalibur packages live
under `morgana/excalibur/mobile/drozer/`. See
`Morgana/docs/DROZER_ARCHITECTURE.md` and the Mobile Lab section of this guide.

## OWASP MASTG + Hacking Playground

- **MASTG test library + MASVS coverage** — served from `mastg-coverage.json`
  (this directory) and surfaced in Morgana at `/api/v2/mastg/*` and the Mobile
  Lab "MASTG Tests" UI. Tests are manual procedure cards, not fake automation.
- **Hacking Playground apps** — `catalog.json` `apps` array (3 apps) and
  `services` array (1 Rails backend). Apps are App Assets, not Scripts.
- **Playground templates** — `android-mastg-playground-lab`,
  `ios-mastg-playground-lab`.
- Updater: `morgana/excalibur/tools/update-mastg.ps1`.
- Docs: `Morgana/docs/OWASP_MASTG_INTEGRATION.md` and the other `OWASP_MASTG_*.md` guides.

## App Licensing

Only redistributable lab assets are published here. Unlicensed/proprietary apps
are marked `reference-only` and never packaged. Morgana records SHA-256, source,
and license status per asset. Hacking Playground apps are GPL-3.0; binaries are
not re-distributed (source-pinned, reproducible build).

## Reference

- Architecture: `Morgana/docs/MOBILE_LAB_ARCHITECTURE.md`
- User guide: `Morgana/docs/MOBILE_LAB_USER_GUIDE.md`
- Troubleshooting: `Morgana/docs/MOBILE_LAB_TROUBLESHOOTING.md`
