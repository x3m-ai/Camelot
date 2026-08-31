# Drozer Android Application-Security Packs

Complete, source-faithful [ReversecLabs/drozer](https://github.com/ReversecLabs/drozer) module corpus plus the external [drozer-modules](https://github.com/ReversecLabs/drozer-modules) tree, published as a dedicated first-class Morgana provider for authorized Android application-model assessment.

- Drozer core source commit: `d992f6378d42680ea96ee03eff4117f150e1049c` (v3.2.0, BSD-3-Clause)
- drozer-modules source commit: `c6fb1570163e3347e11c8d8589d51b88931137dd`
- drozer-agent commit: `c1f18ceb6f8464811e9e4f9d57ad8cb38de4e339` (package `com.reversec.dz`, BSD-3-Clause)
- Published Scripts: 79 (65 core + 14 external)
- Packages: 8 (one per namespace)
- Manual/support/internal: 23 (3 manual + 20 framework-internal)
- Source reconciliation: PASS (no silent loss)

## What Drozer is

Drozer is a modular Android application-security assessment framework. It
enumerates a target application's attack surface (packages, activities,
services, broadcast receivers, content providers, permissions, Intents/IPC)
through the official `drozer-agent` running on the device, using the
`drozer console connect` non-interactive runtime over `adb forward tcp:31415`.

- Core modules ship with the `drozer` repository itself (`src/drozer/modules/`).
- External modules live in the `drozer-modules` community repository.

## Why Drozer is independent from Frida Mobile and MEDUSA

Drozer content is published independently even when similar functionality
exists in Frida Mobile or MEDUSA. This is intentional: Drozer uses a
device-side agent + IPC model rather than runtime instrumentation, so it covers
a different compatibility surface. Operators choose the provider that best
fits the target application.

- Drozer Scripts suppressed due to MEDUSA overlap: **0**
- Drozer Scripts suppressed due to Frida Mobile overlap: **0**
- Drozer Scripts suppressed due to semantic similarity: **0**

## Runtime architecture

```text
Morgana Server
      |
Windows / Linux / macOS host Agent (Mobile Lab Host)
      |
generic morgana_drozer_runner.py asset (executor=python)
      |
pinned isolated Drozer runtime (drozer console connect --no-color)
      |
adb forward tcp:31415  ->  device drozer-agent  ->  target application
```

The Morgana Agent runs on the **Host**; the Android-side component is the
official `drozer-agent`. No second device-management subsystem is created.

## Module arguments

Drozer module options become Morgana runtime tag parameters. At execution time
Morgana tag substitution fills the operator-supplied or default value, and the
generic runner passes them to `drozer console` with proper shell quoting. The
result is captured via the `MORGANA_RESULT_METADATA=<json>` marker line and
parsed by the existing `morgana-marker-v1` result parser.

## Device prerequisites

- Morgana Mobile Lab Host with the pinned isolated Drozer runtime
  (default `C:/ProgramData/Morgana/mobile-lab/runtimes/drozer/3.2.0`)
- Android Emulator or authorized Physical Android device with `adb` access
- Official `drozer-agent` installed on the target device (package
  `com.reversec.dz`)
- Authorized target package (supplied as the `drozer_serial` + package arguments)

## Operational risk

| Level | Namespaces |
|---|---|
| observe | app, information, scanner, tools, auxiliary |
| interact | post |
| modify | shell |
| disrupt | exploit |

See `Morgana/docs/DROZER_RISK.md` for the full risk model.

## Known limitations

- Android-only. Apple Simulator / iOS is explicitly NOT_SUPPORTED.
- `payload` modules are classified as manual (not directly executable) and are
  not published as standalone Scripts.
- 20 core modules are framework-internal (no direct execution path) and are
  reported as support/internal, never silently dropped.
- Full-corpus runtime validation is intentionally left to isolated operator
  mobile labs; static/source validation is complete.
