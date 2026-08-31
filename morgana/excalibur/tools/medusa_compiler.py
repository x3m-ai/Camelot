#!/usr/bin/env python3
"""
medusa_compiler.py — Source-faithful MEDUSA module compiler.

Assembles a single runtime-ready Frida JavaScript file from:
    - the MEDUSA core JS runtime (globals, beautifiers, utils, platform core)
    - the module Code (wrapped exactly like upstream medusa.py / medusa_ios.py)
    - a JNIEnv prolog for JNICalls modules (Android)
    - optional runtime parameter substitution for module Options.

The output is consumed by the existing Morgana Frida executor
(executor=frida, the agent wraps the JS source in a {"source","config"} envelope).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

MEDUSA_REPO = "Ch0pin/medusa"

# Android compile order (mirrors medusa.py do_compile):
#   [native bridge] + globals + beautifiers + utils + android_core + Java.perform wrapper + module
ANDROID_CORE = ["globals.js", "beautifiers.js", "utils.js", "android_core.js"]

# iOS compile order (mirrors medusa_ios.py do_compile):
#   frida_objc_bridge + frida_module_bridge (frida>=17) + globals + beautifiers + utils + ios_core
IOS_CORE = ["globals.js", "beautifiers.js", "utils.js", "ios_core.js"]

# Upstream JNICalls prolog (Android only).
JNI_PROLOG = """
var jnienv_addr = 0x0;
try{
    Java.perform(function(){jnienv_addr = Java.vm.getEnv().handle.readPointer();});
    console.log("[+] Hooked successfully, JNIEnv base address: " + jnienv_addr);
}
catch(err){
    console.log('Error:'+err);
}
"""

ANDROID_PREAMBLE = (
    "Java.perform(function() {\ntry {\n"
    "setTimeout(displayAppInfo,500);\n"
)
ANDROID_EPILOG = (
    "}\n"
    "catch(error){\n"
    '    colorLog("------------Error Log start-------------",{ c:Color.Red })\n'
    "    console.log(error.stack);\n"
    '    colorLog("------------Error Log EOF---------------",{ c:Color.Red })\n'
    "} });\n"
)

IOS_PREAMBLE = "try \n{\n"
IOS_EPILOG = (
    "}\n"
    "catch(error){\n"
    '    colorLog("------------Error Log start-------------",{ c:Color.Red })\n'
    "    console.log(error.stack);\n"
    '    colorLog("------------Error Log EOF---------------",{ c:Color.Red })\n'
    "};\n"
)


def load_core(core_dir: Path, platform: str) -> str:
    """Load and concatenate the MEDUSA core JS runtime for a platform."""
    files = ANDROID_CORE if platform == "android" else IOS_CORE
    parts: list[str] = []
    for filename in files:
        path = core_dir / filename
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts) + "\n"


def _value_template(opt_type: str, key: str) -> str:
    """Render the runtime placeholder template for an Option, preserving type semantics."""
    t = (opt_type or "string").strip().lower()
    if t in {"boolean", "bool", "integer", "int", "float", "number"}:
        return f"#{{{key}}}"
    # string and unknown types stay quoted (source-faithful)
    return f"'#{{{key}}}'"


_OPTION_VALUE_RE = re.compile(
    r"(__[A-Za-z0-9_]+__)(\s*=\s*)(?:'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|[^;,\n]+)"
)


def substitute_options(code: str, options: list[dict]) -> tuple[str, list[str]]:
    """
    Replace MEDUSA `__name__ = value` declarations with Morgana tag placeholders.

    Only declarations that actually exist in the source are substituted, so the
    upstream default stays in place when a module declares a constant the operator
    does not override. Returns the modified code and the list of option keys whose
    markers were wired into the source.
    """
    added: list[str] = []
    by_key = {
        str(opt.get("name") or "").strip(): opt
        for opt in options
        if isinstance(opt, dict) and str(opt.get("name") or "").strip()
    }

    def _repl(match: re.Match) -> str:
        marker = match.group(1)
        key = marker.strip("__").strip()
        opt = by_key.get(key)
        if opt is None:
            return match.group(0)
        if key not in added:
            added.append(key)
        return marker + match.group(2) + _value_template(str(opt.get("type") or "string"), key)

    return _OPTION_VALUE_RE.sub(_repl, code), added


def compile_module(
    module: dict[str, Any],
    core_dir: Path,
    *,
    substitute: bool = True,
) -> Optional[tuple[str, list[str]]]:
    """
    Compile one parsed MEDUSA module into a standalone Frida JS program.

    Returns (compiled_js, wired_option_keys), or None when the module has no
    executable Code (template/empty/scratchpad). `wired_option_keys` lists the
    Option names whose `__name__` markers were actually substituted into the
    source and therefore need a runtime tag.
    """
    code = (module.get("code") or "").strip()
    if not code:
        return None

    platform = module.get("platform") or "android"
    core = load_core(core_dir, platform)

    options = module.get("options") or []
    wired: list[str] = []
    if substitute and options:
        code, wired = substitute_options(code, options)

    if platform == "ios":
        body = IOS_PREAMBLE
        body += _wrap_module(code, module)
        body += IOS_EPILOG
        return core + body, wired

    body = ANDROID_PREAMBLE
    if "jnialls" in (module.get("category") or "").lower() or "JNICalls" in (module.get("source_path") or ""):
        body += JNI_PROLOG
    body += _wrap_module(code, module)
    body += ANDROID_EPILOG
    return core + body, wired


def _wrap_module(code: str, module: dict[str, Any]) -> str:
    """Wrap one module's Code in the upstream try/catch + colorLog guard."""
    module_name = module.get("name") or module.get("display_name") or "medusa-module"
    name_literal = re.sub(r"[^A-Za-z0-9_./ -]", "", module_name)
    return (
        "try {\n"
        f"// Module: {name_literal}\n"
        f"{code}\n"
        "} catch (error) {\n"
        f'colorLog("[module failed] " + {name_literal!r}, {{ c: Color.Red }});\n'
        "console.log(error && error.stack ? error.stack : error);\n"
        "}\n"
    )


# Morgana runtime placeholders are not valid standalone JavaScript identifiers
# where a bare (unquoted) placeholder is used for numeric/boolean options. For
# static syntax checking only, replace every `#{key}` with a benign value.
_PLACEHOLDER_RE = re.compile(r"#\{[^{}]+\}")


def js_syntax_valid(code: str, timeout: int = 20) -> tuple[bool, str]:
    """Static JavaScript syntax check via `node --check` when available."""
    if not code.strip():
        return False, "empty source"
    try:
        node = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=timeout
        )
        if node.returncode != 0:
            return True, "node not available; syntax check skipped"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, "node not available; syntax check skipped"

    # Neutralize runtime tag placeholders for syntax-only validation.
    checked = _PLACEHOLDER_RE.sub("0", code)

    with tempfile.TemporaryDirectory(prefix="medusa-js-check-") as temporary:
        path = Path(temporary) / "module.js"
        path.write_text(checked, encoding="utf-8")
        result = subprocess.run(
            ["node", "--check", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, ""
        return False, (result.stderr or "").replace(str(path), "<module>.js").strip()
