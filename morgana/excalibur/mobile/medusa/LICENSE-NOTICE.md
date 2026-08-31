# MEDUSA License Notice

The MEDUSA provider packages source-faithful content from:

- **Project:** MEDUSA
- **Author:** Ch0pin
- **Repository:** https://github.com/Ch0pin/medusa
- **Pinned source commit:** `8c62447d082f8612aeb9e07f8d8c20d8fa5f1fbb`
- **Stable release reference:** v3.9.6
- **License:** GNU General Public License v3.0 (GPL-3.0)

The upstream MEDUSA project is distributed under the GPL-3.0 license. The complete license text is available at:

- https://www.gnu.org/licenses/gpl-3.0.html
- https://github.com/Ch0pin/medusa/blob/master/LICENSE

The Morgana integration converts MEDUSA module source (`.med`, `.imed`) and standalone snippets into Excalibur package JSON for execution through the Morgana Frida runtime. This conversion preserves source identity, provenance, and license attribution. No MEDUSA source content was modified except:

1. `Options` declarations (`__name__ = value`) are substituted with Morgana runtime tag placeholders (`#{name}`) so operators can supply values at execution time.
2. Module `Code` is wrapped in the same try/catch guards the upstream compiler uses.

MEDUSA is intentionally independent from the Frida Mobile provider. GPL-3.0 attribution applies to the MEDUSA-sourced Scripts in this directory; it does not override the separate license inventory of the Frida Mobile provider.
