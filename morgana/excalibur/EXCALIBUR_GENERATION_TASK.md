# Excalibur Pack Generation Task — Handoff for New Agent Session

## OBIETTIVO

Generare tutti gli script Excalibur mancanti per i tre domini MITRE ATT&CK (Enterprise, ICS, Mobile)
coprendo **Windows** e **Linux**, per ogni tattica e tutte le sue tecniche + sotto-tecniche.

Il risultato finale sarà una libreria completa di pack JSON pronti per Morgana, organizzati per dominio e piattaforma.

---

## STATO ATTUALE (cosa abbiamo già)

Tutti i file sono in: `C:\Users\ninoc\OfficeAddinApps\Camelot\morgana\excalibur\`

### Pack esistenti — Enterprise, Windows only

| Tactic | File | Tecniche coperte | Note |
|--------|------|-----------------|------|
| TA0001 Entra ID | excalibur-entraid-emulation-pack.json | T1531, T1098, T1136, T1556, T1484, T1528, T1078, T1110, T1090 | Azure identity only, NON riscrivere |
| TA0002 Execution | excalibur-execution-emulation-pack.json | T1047, T1053, T1059+sub, T1072, T1106, T1129, T1204, T1559, T1569, T1620, T1648, T1651 | v2.0.0 con 17 script |
| TA0003 Persistence | excalibur-persistence-emulation-pack.json | T1037, T1053, T1098, T1136, T1197, T1505, T1543, T1546, T1547, T1574 | 10 script |
| TA0004 PrivEsc | excalibur-privesc-emulation-pack.json | T1053, T1068, T1078, T1134, T1484, T1546, T1548, T1574, T1611 | 10 script |
| TA0005 DefEvasion | excalibur-defenseevasion-emulation-pack.json | T1027, T1036, T1055, T1070, T1112, T1218, T1220, T1497, T1562, T1564 | 10 script |
| TA0006 CredAccess | excalibur-credaccess-emulation-pack.json | T1003, T1040, T1056, T1110, T1187, T1528, T1539, T1552, T1555, T1558 | 10 script |
| TA0007 Discovery | excalibur-discovery-emulation-pack.json | T1007, T1012, T1016, T1018, T1049, T1057, T1069, T1082, T1087, T1135 | 10 script |
| TA0008 LateralMov | excalibur-lateralmovement-emulation-pack.json | T1021, T1047, T1080, T1534, T1550, T1563, T1570 | 10 script |
| TA0009 Collection | excalibur-collection-emulation-pack.json | T1005, T1039, T1074, T1113, T1114, T1115, T1119, T1123, T1125, T1560 | 10 script |
| TA0010 Exfiltration | excalibur-exfiltration-emulation-pack.json | T1011, T1020, T1022, T1029, T1030, T1041, T1048, T1052, T1537, T1567 | 10 script |
| TA0011 C2 | excalibur-c2-emulation-pack.json | T1001, T1071, T1090, T1095, T1102, T1219, T1568, T1572, T1573 | 10 script |
| TA0040 Impact | excalibur-impact-emulation-pack.json | T1485, T1486, T1489, T1490, T1491, T1495, T1498, T1499, T1529, T1561 | 10 script |
| TA0043 Recon | excalibur-reconnaissance-emulation-pack.json | T1589, T1590, T1591, T1592, T1593, T1594, T1595, T1596, T1597, T1598 | 10 script |

### COSA MANCA (da generare)

1. **Enterprise Linux** — tutti i 13 pack riscritti con executor `bash` per Linux
2. **Enterprise Windows — sub-tecniche** — ogni pack attuale copre solo le tecniche parent; mancano tutte le sub-tecniche (es. T1059.001 PowerShell, T1059.004 Unix Shell, T1547.001 Registry Run Keys, ecc.)
3. **ICS domain** — tutti i pack per Windows e Linux
4. **Mobile domain** — tutti i pack per Android e iOS

---

## OUTPUT STRUCTURE RICHIESTA

```
Camelot/morgana/excalibur/
  enterprise/
    windows/
      excalibur-enterprise-windows-TA0002-execution.json
      excalibur-enterprise-windows-TA0003-persistence.json
      excalibur-enterprise-windows-TA0004-privesc.json
      excalibur-enterprise-windows-TA0005-defenseevasion.json
      excalibur-enterprise-windows-TA0006-credaccess.json
      excalibur-enterprise-windows-TA0007-discovery.json
      excalibur-enterprise-windows-TA0008-lateralmovement.json
      excalibur-enterprise-windows-TA0009-collection.json
      excalibur-enterprise-windows-TA0010-exfiltration.json
      excalibur-enterprise-windows-TA0011-c2.json
      excalibur-enterprise-windows-TA0040-impact.json
      excalibur-enterprise-windows-TA0043-reconnaissance.json
    linux/
      excalibur-enterprise-linux-TA0002-execution.json
      excalibur-enterprise-linux-TA0003-persistence.json
      ... (stessa struttura)
  ics/
    windows/
      excalibur-ics-windows-TA0108-execution.json
      ...
    linux/
      ...
  mobile/
    android/
      excalibur-mobile-android-TA0041-execution.json
      ...
    ios/
      ...
```

**Regola critica:** 1 file JSON = 1 tattica + 1 piattaforma. Contiene TUTTE le tecniche + sub-tecniche di quella tattica per quella piattaforma. NON creare un file per ogni tecnica.

---

## FORMATO PACK JSON (obbligatorio — non deviare)

Ogni file JSON deve avere questa struttura esatta. Studia il file di riferimento:
`C:\Users\ninoc\OfficeAddinApps\Camelot\morgana\excalibur\excalibur-persistence-emulation-pack.json`

### Schema di alto livello

```json
{
  "package_id": "excalibur-enterprise-windows-TA0003-persistence",
  "package_name": "Excalibur - Enterprise Windows Persistence (TA0003)",
  "version": "1.0.0",
  "description": "...",
  "author": "X3M.AI",
  "created": "2026-06-16",
  "mitre_domain": "enterprise-attack",
  "mitre_tactic": "TA0003",
  "mitre_tactic_name": "Persistence",
  "platform": "windows",
  "prerequisites": ["..."],
  "tag_categories": [ ... ],
  "scripts": [ ... ],
  "chains": [ ... ]
}
```

### Schema di ogni script

```json
{
  "id": "Excalibur - Enterprise-Windows-T1547.001-Registry Run Keys",
  "name": "Excalibur - Enterprise-Windows-T1547.001-Registry Run Keys",
  "description": "Descrizione dettagliata tecnica del test, cosa simula, quale telemetria genera, quale Sentinel rule colpisce.",
  "tactic": "Persistence",
  "tcode": "T1547.001",
  "technique_name": "Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder",
  "executor": "powershell",
  "platform": "windows",
  "required_tags": ["excalibur_temp_dir"],
  "command": "Write-Host '[START] T1547.001 ...'; ... Write-Host '[SUCCESS] ...'",
  "cleanup_command": "...",
  "source": "excalibur",
  "package_id": "excalibur-enterprise-windows-TA0003-persistence"
}
```

Per Linux: `"executor": "bash"`, `"platform": "linux"`

### Schema di ogni chain

```json
{
  "id": "excalibur-enterprise-windows-TA0003-persistence-chain-T1547.001",
  "name": "T1547.001 - Registry Run Keys Persistence",
  "description": "...",
  "steps": [
    { "script_id": "Excalibur - Enterprise-Windows-T1547.001-Registry Run Keys", "order": 1 }
  ],
  "package_id": "excalibur-enterprise-windows-TA0003-persistence"
}
```

### Schema tag_category

```json
{
  "category_id": "common_local",
  "label": "Common - Local Environment",
  "description": "...",
  "scope": "local",
  "used_by_tcodes": ["T1547.001", "T1547.002"],
  "tags": [
    {
      "key": "excalibur_temp_dir",
      "label": "Temp Directory (Defender-excluded)",
      "description": "...",
      "default": "C:\\ProgramData\\Morgana\\temp",
      "example": "C:\\ProgramData\\Morgana\\temp",
      "sensitive": false,
      "required": false
    }
  ]
}
```

---

## REGOLE OBBLIGATORIE PER GLI SCRIPT

1. **Nessun emoji** — mai. Usare solo `[START]`, `[SUCCESS]`, `[ERROR]`, `[INFO]`, `[WARN]`
2. **Tag placeholder** — ogni `#{tag_key}` usato nel `command` DEVE essere in `required_tags`
3. **cleanup_command** — sempre presente, deve annullare esattamente quanto fatto dal `command`
4. **Temp files Windows** — sempre in `#{excalibur_temp_dir}` (default `C:\ProgramData\Morgana\temp`) — MAI in `C:\Windows\Temp\`
5. **Temp files Linux** — sempre in `/tmp/morgana-test/` o variabile tag
6. **sensitive: true** — obbligatorio per password, client_secret, API key, token
7. **Error handling** — ogni script PowerShell usa `try/catch`, ogni bash usa `set -e` o controlli espliciti
8. **Test-safe** — nessuno script deve causare danni reali. Usare TEST-NET IP (198.51.100.x) per target di rete
9. **Cleanup automatico** — artefatti (file, task, registry keys, utenti) rimossi nel `command` stesso + nel `cleanup_command`
10. **Exit pulito** — ogni script deve terminare con `[SUCCESS]` o `[ERROR]` chiari
