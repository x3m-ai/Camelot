# Camelot - Community Repository Guide

> **Publisher:** X3M.AI Ltd (UK) | **Author:** Nino Crudele
> **Repo:** `x3m-ai/Camelot` (public) | **GitHub:** https://github.com/x3m-ai/Camelot

---

## UNIFIED WORKSPACE

This repo is part of the **X3M.AI multi-root workspace** (`X3MAI.code-workspace` in `C:\Users\ninoc\OfficeAddinApps\`).
All three projects are open simultaneously in the same VS Code window:

| Folder | Repo | copilot-instructions | Role |
|--------|------|----------------------|------|
| `Merlino/` | `x3m-ai/Merlino` (private) | `Merlino/.github/copilot-instructions.md` | Excel Add-in — command & intelligence layer |
| `Morgana/` | `x3m-ai/Morgana` (public) | `Morgana/.github/copilot-instructions.md` | Red Team Server + Agent — execution layer |
| `Camelot/` | `x3m-ai/Camelot` (public) | `Camelot/.github/copilot-instructions.md` | Community releases, installers, templates, labs |

All three `copilot-instructions.md` files are loaded simultaneously by Copilot when the workspace is open.

---

## WHAT IS CAMELOT

**Camelot is the public community repository** for both Merlino and Morgana. It is the single point of distribution for everything that end users download, install, or reference.

Merlino is a private development repo. Morgana is public. When something is ready for the community, it is published here.

**This repo is PUBLIC** — never commit sensitive data, API keys, credentials, or internal notes.

---

## CRITICAL CONSTRAINTS

1. **NEVER commit or push** — Do NOT run `git commit` or `git push` unless the user explicitly asks for it. No exceptions.
2. **This repo is PUBLIC** — Everything committed here is visible to anyone on the internet. No secrets, no internal paths, no credentials.
3. **No source code** — Camelot contains releases, templates, data, and docs. Source code lives in Merlino and Morgana.
4. **Morgana installer is the critical asset** — `morgana/Install/Morgana-Server-Setup.exe` must always match the version stated in `morgana/Install/README.md`.

---

## CONTENT STRUCTURE

```
morgana/
  Install/
    Morgana-Server-Setup.exe   Current release installer (updated on every Morgana release)
    README.md                  Installation guide (version header updated on every release)
  excalibur/
    catalog.json               Master pack index fetched by Morgana UI on Refresh catalog
    art/                       ART packs — Red Canary Atomic Red Team (1603 scripts, 13 tactics)
      art-exec-v1.json         One pack per MITRE tactic, naming: art-{tactic_slug}-v1.json
      README.md                Documentazione completa dell'integrazione ART
    tools/
      convert_atomics.py       Converter YAML -> Excalibur Pack JSON (richiede pyyaml)
      test_art_import.py       Test import pack contro server Morgana locale
      update-art-packs.ps1     Pipeline completa: pull Red Canary -> convert -> commit+push

merlino/                       Merlino community templates and resources

data/                          Shared community data
  mitre/                       MITRE ATT&CK mappings and catalogues

standard-templates/            Standard Merlino Excel templates (.xlsx)

laboratories/                  Lab guides for Purple Teaming exercises

docs/
  morgana/                     Morgana getting-started docs for end users

powershell-export-scripts/     Community PowerShell utility scripts
```

---

## PUBLISH WORKFLOW

Camelot is updated by the Morgana release pipeline:

1. `Morgana/scripts/01-build-installer.ps1` builds, signs, verifies and **stages**
   the complete set in `morgana/Install/`: installer, AI runtime, README,
   manifest, checksums, release feed and notices. It performs no upload, commit
   or push.
2. `Morgana/scripts/02-publish-installer.ps1` is the separate explicit publish
   step. Run it only with authorization.
3. The generated `morgana/Install/README.md` header, `release-manifest.json`,
   `release.json` and `SHA256SUMS.txt` are authoritative. Do not hand-edit the
   version header or copy a random EXE.
4. `release.json` is the current feed. `version.json` is the legacy feed for
   already-installed older clients and has a separate contract; do not
   "align" it by simply changing the number.
5. Public metadata must use artifact names, URLs and relative paths. Do not
   publish absolute build-machine paths.
6. Commit and push only after explicit authorization.

### README VERSION HEADER

The build generates the first content line of `morgana/Install/README.md` from
the release tag. Do not edit it independently. If the installer ProductVersion
and the release tag differ, stop: align the version source and rebuild.

```text
> **Current release: vX.Y.Z** (DD Month YYYY) — short description
```

### Community content

- Templates → `standard-templates/` or `merlino/`
- Lab guides → `laboratories/`
- Data files → `data/`
- Morgana docs → `docs/morgana/`
