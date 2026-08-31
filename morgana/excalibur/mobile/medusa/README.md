# MEDUSA Mobile Instrumentation Packs

Complete, source-faithful [Ch0pin/medusa](https://github.com/Ch0pin/medusa) module corpus, published as a dedicated first-class Morgana provider for authorized Android and iOS runtime instrumentation.

- Source commit: `8c62447d082f8612aeb9e07f8d8c20d8fa5f1fbb` (v3.9.6)
- License: GPL-3.0 (see `LICENSE-NOTICE.md`)
- Published Scripts: 147 (133 modules + 14 standalone snippets)
- Packages: 38 (33 Android + 5 iOS)
- Manual/unsupported: 4 (empty scratchpads/templates + 1 upstream iOS brace defect)
- Source reconciliation: PASS

## What MEDUSA is

MEDUSA is a modular runtime framework/script repository for Android and iOS penetration testing, malware analysis, and dynamic application analysis built on Frida. Modules are JSON records with `Name`, `Description`, `Help`, `Code`, and optional `Options`.

- Android modules use the `.med` extension.
- iOS modules use the `.imed` extension.
- Standalone Frida snippets live under `snippets/`.

## Why MEDUSA is independent from Frida Mobile

MEDUSA content is published independently even when similar functionality exists in the Frida Mobile provider. This is intentional: different source implementations can have different compatibility, hook coverage, framework/version support, and runtime behavior. Operators choose the provider/implementation that best fits the target application.

- MEDUSA Scripts suppressed due to Frida overlap: **0**
- MEDUSA Scripts suppressed due to semantic similarity: **0**
- Existing Frida content removed: **0**

## Runtime architecture

```text
Morgana Server
      ↓
Windows / Linux / macOS host Agent
      ↓
MEDUSA compiler (core JS + module Code)
      ↓
existing Morgana Frida executor (executor=frida)
      ↓
USB / ADB / network-connected Android or iOS device/emulator
      ↓
target application process
```

The Morgana Agent is **not** installed on the mobile device.

## Module Options

MEDUSA `Options` become Morgana runtime parameters. At compile time each `__name__ = value` declaration is rewritten to a `#{name}` placeholder; at execution time Morgana tag substitution fills the operator-supplied or default value. String options stay quoted; boolean/numeric options are unquoted.

Example — `helpers/location_spoof`:

```text
Options:
  latitude  (string, default 37.9715)
  longitude (string, default 23.7267)

Compiled declaration:
  let __latitude__ = '#{latitude}';
  let __longitude__ = '#{longitude}';
```

## Device prerequisites

- Morgana host Agent with a compatible Frida CLI in `PATH`
- Android: `adb` access + Frida Server on device/emulator
- iOS: jailbroken/instrumentable device with Frida Gadget, or a compatible Frida remote
- Authorized target package/bundle ID (supplied as the `mobile_app_id` tag)

## Operational risk

| Level | Example |
|---|---|
| observe | API/class enumeration, logging, tracing |
| interact | traffic/database/memory tracing |
| modify | SSL pinning bypass, location spoofing, root-detection bypass |
| disrupt | modules with materially disruptive behavior |

## Known limitations

- One upstream iOS module (`modules/ios/helpers/dump_ios_url_scheme.imed`) has an upstream brace defect and is published as manual rather than executable.
- Empty scratchpads/templates are classified as manual.
- Full-corpus runtime validation is intentionally left to isolated operator mobile labs.
