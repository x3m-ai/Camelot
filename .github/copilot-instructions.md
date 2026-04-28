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

Camelot is updated as part of the **Morgana or Merlino release pipeline**:

### When a new Morgana version is released:
1. New `Morgana-Server-Setup.exe` is built in the Morgana repo (`scripts/build-installer.ps1`)
2. The build script **automatically** copies the installer + raw EXE + `version.json` to `Merlino/docs/morgana/` (primary CDN at `https://merlino.x3m.ai/morgana/`)
3. File is also copied to `morgana/Install/Morgana-Server-Setup.exe` here in Camelot (overwrite)
4. `morgana/Install/README.md` version header is updated
5. Commit + push to Camelot and Merlino (user must ask explicitly)

> **Note:** The Morgana in-app auto-update system fetches `https://merlino.x3m.ai/morgana/version.json`. Camelot's `morgana/Install/version.json` is kept in sync but is no longer the primary source.

### When new community content is added:
- Templates → `standard-templates/` or `merlino/`
- Lab guides → `laboratories/`
- Data files → `data/`
- Morgana docs → `docs/morgana/`

---

## README VERSION HEADER FORMAT

The first content line of `morgana/Install/README.md` must always be:
```
> **Current release: vX.Y.Z** (DD Month YYYY) — short description of what changed
```
