#!/usr/bin/env python3
"""Deterministic Frida mobile platform, framework, scope, behavior, and API classification."""

from __future__ import annotations

import re
from typing import Any

from frida_sources import FridaSource

API_PATTERNS = {
    "Java.perform": r"\bJava\.perform\b",
    "Java.use": r"\bJava\.use\b",
    "Java.choose": r"\bJava\.choose\b",
    "Java.cast": r"\bJava\.cast\b",
    "Java.enumerateLoadedClasses": r"\bJava\.enumerateLoadedClasses(?:Sync)?\b",
    "ObjC.available": r"\bObjC\.available\b",
    "ObjC.classes": r"\bObjC\.classes\b",
    "Interceptor.attach": r"\bInterceptor\.attach\b",
    "Interceptor.replace": r"\bInterceptor\.replace\b",
    "Module.findExportByName": r"\bModule\.(?:find|get)ExportByName\b",
    "Module.enumerateExports": r"\bModule\.enumerateExports(?:Sync)?\b",
    "Module.enumerateSymbols": r"\bModule\.enumerateSymbols(?:Sync)?\b",
    "Memory": r"\bMemory\.",
    "Process": r"\bProcess\.",
    "Stalker": r"\bStalker\.",
    "Thread.backtrace": r"\bThread\.backtrace\b",
    "DebugSymbol": r"\bDebugSymbol\.",
    "Backtracer": r"\bBacktracer\.",
    "NativeFunction": r"\bNativeFunction\b",
    "NativeCallback": r"\bNativeCallback\b",
    "rpc.exports": r"\brpc\.exports\b",
    "send": r"\bsend\s*\(",
    "recv": r"\brecv\s*\(",
}

FRAMEWORK_PATTERNS = {
    "flutter": r"\bflutter\b|libflutter|dart(?:_define|:)",
    "react-native": r"react[ -]?native|com\.facebook\.react|reactnativejs",
    "xamarin": r"\bxamarin\b|mono_|monodroid",
    "unity-il2cpp": r"\bunity\b|il2cpp|libunity",
    "cordova": r"\bcordova\b",
    "ionic": r"\bionic\b",
}

BEHAVIOR_PATTERNS: list[tuple[str, str]] = [
    ("tls-pinning-testing", r"ssl|tls|pinning|trustmanager|sectrust|certificate"),
    ("root-state-testing", r"\broot\b|magisk|su\b"),
    ("jailbreak-state-testing", r"jailbreak|cydia|substrate"),
    ("debugger-detection-testing", r"debugger|ptrace|anti-debug|isdebuggerconnected"),
    ("instrumentation-detection-testing", r"anti-frida|frida detection|gum-js-loop|gmain"),
    ("emulator-detection-testing", r"emulator|genymotion|goldfish|qemu"),
    ("crypto-observation", r"crypto|cipher|encrypt|decrypt|aes|rsa|commoncrypto|cccrypt"),
    ("keystore-keychain", r"keystore|keychain|secitem"),
    ("network-observation", r"okhttp|urlsession|urlconnection|http|socket|network|proxy"),
    ("biometrics", r"biometric|fingerprint|faceid|touchid|localauthentication"),
    ("webview", r"webview|wkwebview|uiwebview"),
    ("filesystem", r"filemanager|filesystem|open\(|read\(|write\("),
    ("database", r"sqlite|database|realm"),
    ("clipboard", r"clipboard|pasteboard"),
    ("screenshot", r"screenshot|uigraphics|drawviewhierarchy"),
    ("location", r"location|gps|cllocation"),
    ("ipc", r"intent|binder|xpc|ipc"),
    ("native-hooking", r"interceptor\.(?:attach|replace)|nativefunction|module\.(?:find|get)export"),
    ("method-hooking", r"\.implementation\s*=|method\.implementation|objc\.implement"),
    ("enumeration", r"enumerate|classes|methods|modules|exports|imports"),
    ("runtime-tracing", r"trace|stalker|backtrace|observer|monitor|hook"),
    ("integrity-control-testing", r"integrity|signature|tamper"),
]

ATTACK_BY_BEHAVIOR: dict[str, list[str]] = {
    "runtime-tracing": ["T1418"],
    "enumeration": ["T1418"],
    "filesystem": ["T1420"],
    "keystore-keychain": ["T1636.002"],
    "clipboard": ["T1414"],
    "screenshot": ["T1513"],
    "location": ["T1430"],
}


def classify(source: FridaSource, overrides: dict[str, Any] | None = None) -> FridaSource:
    overrides = overrides or {}
    text = f"{source.title}\n{source.description}\n{source.source_metadata.get('source_path', '')}\n{source.source_code}".lower()
    android_score = sum(text.count(value) for value in ("java.perform", "java.use", "android.", "com.android", "dalvik", "okhttp", "trustmanager", "webview", "biometricprompt", "packagemanager"))
    ios_score = sum(text.count(value) for value in ("objc.", "foundation", "uikit", "sectrust", "nsurl", "uiapplication", "keychain", "commoncrypto", "nsstring", "ios"))
    hints = source.source_metadata.get("platform_hint", [])
    android_score += 2 if "android" in hints else 0
    ios_score += 2 if "ios" in hints else 0
    if android_score and ios_score:
        platform = "universal-native"
    elif android_score:
        platform = "android"
    elif ios_score:
        platform = "ios"
    elif re.search(r"interceptor\.|module\.|process\.|nativefunction|memory\.", text):
        platform = "universal-native"
    else:
        platform = "other"

    frameworks = [name for name, pattern in FRAMEWORK_PATTERNS.items() if re.search(pattern, text, re.I)]
    frameworks.extend(value for value in source.source_metadata.get("framework_hint", []) if value not in frameworks)
    if not frameworks:
        if platform == "android": frameworks = ["native-java"]
        elif platform == "ios": frameworks = ["native-objc"]
        else: frameworks = ["generic-native"]

    app_id = ""
    app_match = re.search(r"\b(?:com|org|net|io)\.[a-z0-9_.-]+\b", text, re.I)
    if app_match:
        candidate = app_match.group(0)
        if not candidate.lower().startswith(("com.android", "com.apple", "com.facebook.react", "java.")):
            app_id = candidate
    version = ""
    version_match = re.search(r"\b(?:version|tested on|v)\s*(\d+(?:\.\d+){1,3})\b", text, re.I)
    if version_match: version = version_match.group(1)
    if version:
        scope = "version-specific"
    elif app_id or re.search(r"instagram|snapchat|facebook|twitter|whatsapp|spotify|tiktok", text, re.I):
        scope = "app-specific"
    elif any(name not in {"native-java", "native-objc", "generic-native"} for name in frameworks):
        scope = "framework-specific"
    elif re.search(r"okhttp|trustkit|afnetworking|realm|retrofit", text, re.I):
        scope = "library-specific"
    elif len(source.source_code) < 180 or "snippet" in source.title.lower():
        scope = "research-snippet"
    else:
        scope = "generic"

    behaviors = [name for name, pattern in BEHAVIOR_PATTERNS if re.search(pattern, text, re.I)] or ["other"]
    api_features = [name for name, pattern in API_PATTERNS.items() if re.search(pattern, source.source_code)]
    primary = behaviors[0]
    tcodes = ATTACK_BY_BEHAVIOR.get(primary, [])
    compatibility = "legacy" if re.search(r"Module\.findBaseAddress|Module\.findExportByName|null\.implementation", source.source_code) else "likely-compatible"
    risk = "disrupt" if re.search(r"Process\.kill|exit\s*\(|abort\s*\(", source.source_code) else "modify" if any(value in behaviors for value in ("tls-pinning-testing", "root-state-testing", "jailbreak-state-testing", "debugger-detection-testing", "instrumentation-detection-testing", "integrity-control-testing")) else "interact" if any(value in behaviors for value in ("native-hooking", "method-hooking", "network-observation")) else "observe"
    readiness = "legacy" if compatibility == "legacy" else "app_specific" if scope in {"app-specific", "version-specific"} else "framework_prerequisite" if scope == "framework-specific" else "ready_with_target"

    override = overrides.get(source.source_id, {})
    source.target_platform = override.get("target_platform", platform)
    source.frameworks = sorted(set(override.get("frameworks", frameworks)))
    source.scope = override.get("scope", scope)
    source.behaviors = sorted(set(override.get("behaviors", behaviors)))
    source.primary_behavior = override.get("primary_behavior", primary)
    source.frida_apis = api_features
    source.compatibility_status = override.get("compatibility_status", compatibility)
    source.source_tcodes = override.get("source_tcodes", tcodes)
    source.primary_tcode = source.source_tcodes[0] if source.source_tcodes else "T0000"
    source.risk = override.get("risk", risk)
    source.readiness = override.get("readiness", readiness)
    source.source_metadata.update({"target_app": app_id, "tested_version": version})
    return source