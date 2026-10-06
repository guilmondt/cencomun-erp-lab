"""Publish truthful, sanitized criterion evidence and reproducibility instructions."""

import hashlib, json, re, subprocess, datetime, csv, statistics
from pathlib import Path
from coverage_rules import apply_contract, criterion_status

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/workspace/.local/frappe-integral")
OUT = REPO / "reports/evidence/frappe-core"
REPORT = REPO / "reports/frappe-core-test.md"
GROUPS = ["business", "finance", "http", "recovery", "audit"]
cases = []
missing = []
for name in GROUPS:
    p = OUT / (name + ".json")
    if p.exists():
        for case in json.loads(p.read_text())["cases"]:
            cases.append({**case, "evidence": str(p.relative_to(REPO))})
    else:
        missing.append(name)
contract = json.loads((REPO / "fixtures/ccm-core-v1/coverage-required.json").read_text())
cases, coverage_gaps = apply_contract(cases, contract)
coverage = {"revision": contract["coverage_revision"], "required_groups": len(contract["requirements"]),
            "gaps": coverage_gaps, "status": "UNRUN" if coverage_gaps else "PASS"}
(OUT / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
labels = [
    "Objetos soportados",
    "Core upstream intacto",
    "Permisos en servidor",
    "Transiciones válidas y atómicas",
    "Dinero determinista y TAX01 nativo",
    "Caja inmutable y auditada",
    "Compras por umbral",
    "Banco idempotente",
    "API sin DB directa",
    "MCP vía adaptador",
    "Fixtures compartidos cargados",
    "Búsqueda completa",
    "Regresión tras patch",
    "Setup reproducible",
]
upstream = []
for app in ["frappe", "erpnext"]:
    folder = ROOT / "bench/apps" / app
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=folder, text=True
    ).strip()
    diff = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=folder, text=True
    ).strip()
    tag = subprocess.check_output(
        ["git", "describe", "--tags", "--exact-match"], cwd=folder, text=True
    ).strip()
    upstream.append(
        {
            "app": app,
            "sha": sha,
            "tag": tag,
            "changes": diff.splitlines() if diff else [],
        }
    )
pins = hashlib.sha256((REPO / "versions.lock").read_bytes()).hexdigest()
tags = []
tag_status = []
for app in ["frappe", "erpnext"]:
    command = [
        "git",
        "ls-remote",
        "--tags",
        "https://github.com/frappe/" + app + ".git",
        "refs/tags/v16.36.*",
    ]
    r = subprocess.run(command, capture_output=True, text=True)
    rows = [
        {"sha": line.split()[0], "ref": line.split()[1]}
        for line in r.stdout.splitlines()
        if len(line.split()) == 2
    ]
    tag_status.append(
        {
            "app": app,
            "command": " ".join(command),
            "exit_code": r.returncode,
            "tags": rows,
        }
    )
    tags.extend(rows)
# Record rather than execute any change in pins: no later compatible target.
patch = {
    "status": "BLOCKED",
    "current": "v16.36.1",
    "queries": tag_status,
    "reason": "Neither official Frappe nor ERPNext tags provide a compatible patch after v16.36.1 in the pinned 16.36 series. Existing runtime pins stay fixed; baseline suites do not satisfy post-patch scenarios.",
    "dependent_cases": [
        {"case": k, "status": "UNRUN", "blocked_by": "criterion-13"}
        for k in [
            "PATCH-TARGET",
            "PATCH-UPGRADE",
            "PATCH-MIGRATE",
            "PATCH-PLATFORM-FULL-REGRESSION",
            "PATCH-CENCOMUN-FULL-REGRESSION",
            "PATCH-RESTORE",
        ]
    ],
}
(OUT / "patch.json").write_text(json.dumps(patch, indent=2) + "\n")
repro = (
    json.loads((OUT / "reproducibility.json").read_text())
    if (OUT / "reproducibility.json").exists()
    else {"status": "UNRUN"}
)
benchmark = (
    json.loads((OUT / "benchmark.json").read_text())
    if (OUT / "benchmark.json").exists()
    else {"status": "UNRUN"}
)
criteria = []
for i, label in enumerate(labels, 1):
    linked = [c for c in cases if i in c.get("criteria", [])]
    status = criterion_status(linked)
    if i == 2:
        status = (
            "PASS"
            if all(not u["changes"] and u["tag"] == "v16.36.1" for u in upstream)
            else "FAIL"
        )
    if i == 13:
        status = "BLOCKED"
    if i == 14:
        status = (
            "PASS"
            if repro.get("status") == "PASS"
            and repro.get("coverage_revision", 1) >= 2
            and status == "PASS"
            else "FAIL"
            if repro.get("status") == "FAIL"
            or any(c["status"] == "FAIL" for c in linked)
            else "UNRUN"
        )
    if i == 11 and benchmark.get("loaded", {}).get("counts") != {
        "products": 1000,
        "customers": 100,
        "orders": 1000,
        "bank_rows": 1000,
    }:
        status = "FAIL"
    criteria.append(
        {
            "criterion": i,
            "name": label,
            "status": status,
            "cases": [c["case"] for c in linked],
            "evidence": sorted(set(c["evidence"] for c in linked))
            or [
                "reports/evidence/frappe-core/patch.json"
                if i == 13
                else "reports/evidence/frappe-core/build.json"
            ],
        }
    )
    if i == 11:
        criteria[-1]["evidence"].append("reports/evidence/frappe-core/benchmark.json")
    if i == 14:
        criteria[-1]["evidence"].append("reports/evidence/frappe-core/reproducibility.json")
counts = {
    s: sum(c["status"] == s for c in criteria) for s in ["PASS", "FAIL", "BLOCKED", "UNRUN"]
}
core_count = {
    s: sum(c["status"] == s for c in cases)
    for s in ["PASS", "FAIL", "BLOCKED", "UNRUN"]
}
appfiles = [
    p
    for p in (REPO / "labs/frappe/cencomun_erp/cencomun_erp").rglob("*")
    if p.is_file() and "__pycache__" not in str(p) and p.suffix in [".py", ".json"]
]
app_loc = sum(len(p.read_text().splitlines()) for p in appfiles)
source_hashes = [
    {
        "file": str(p.relative_to(REPO)),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    for p in sorted(appfiles)
]
# Only aggregate official test results that actually ran, not an exit-zero no-op.
platform_log = ROOT / "logs/core-platform-utils.log"
text = platform_log.read_text() if platform_log.exists() else ""
match = re.search(r"Ran (\d+) tests in ([\d.]+)s", text)
platform = {
    "scope": "Official Frappe utility unit category, not the full Frappe/ERPNext integration suite",
    "tests": int(match.group(1)) if match else 0,
    "seconds": float(match.group(2)) if match else None,
    "status": "PASS" if match and "OK" in text and "FAILED" not in text else "UNRUN",
    "command": "bench --site ccm-core-recovery.test run-tests --module frappe.tests.test_utils --skip-before-tests --test-category unit",
}
official_path = REPO / 'reports/evidence/frappe-official/summary.json'
official = json.loads(official_path.read_text()) if official_path.exists() else {'results': [], 'scope': 'UNRUN'}
commands = (
    json.loads((OUT / "commands.json").read_text())
    if (OUT / "commands.json").exists()
    else {}
)
summary = {
    "platform": "Frappe/ERPNext",
    "branch": subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPO, text=True
    ).strip(),
    "execution_parent_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip(),
    "profile": "LAB-ONLY-v1",
    "source_identity_note": "Execution used the working tree on this parent commit; exact application contents are recorded in source.hashes. The later publication commit includes this evidence.",
    "report_state": "COBERTURA_PENDIENTE" if coverage_gaps or counts["UNRUN"] else "CERRADO_CON_LIMITACIONES",
    "coverage": coverage,
    "criteria": criteria,
    "counts": counts,
    "mandatory_approved": counts["PASS"] == 14
    and core_count["FAIL"] == 0
    and not missing,
    "case_counts": core_count,
    "source": {"files": len(appfiles), "app_loc": app_loc, "hashes": source_hashes},
    "upstream": upstream,
    "versions_lock_sha256": pins,
    "benchmark": benchmark,
    "platform_baseline_subset": platform,
    "platform_official_server_suites": official,
    "cloud_snapshot_verification": {
        "status": "BLOCKED",
        "execution_reported_complete": True,
        "reason": "Separate task completed according to coordinator; evidence and outcome not yet received.",
        "expected_saved_commit": "fcf690dbc58b2b2dcf8d045c49976e3613e804cf",
        "procedure": "docs/FRAPPE_CLOUD_RESTORE_CHECK.md",
        "note": "Criterion 14's LAB site replay is separate evidence; it does not demonstrate restoration in a genuinely new cloud task. The saved environment was not saved/published again.",
    },
    "reproducibility": repro,
    "cases": cases,
    "unrun": patch["dependent_cases"],
    "missing_evidence": missing,
    "commands": commands,
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
rows = [
    "# Core Test de Frappe/ERPNext — LAB-ONLY-v1",
    "",
    f"**{summary['report_state']}: PASS {counts['PASS']}/14, FAIL {counts['FAIL']}/14, BLOCKED {counts['BLOCKED']}/14, UNRUN {counts['UNRUN']}/14.** Los bloqueados mantienen el denominador; este resultado no aprueba integralmente el ERP. Axelor no se ejecutó ni modificó en esta tarea.",
    "",
    f"Cobertura obligatoria: {len(cases)} grupos; {core_count['PASS']} PASS, {core_count['FAIL']} FAIL, {core_count['UNRUN']} UNRUN. Cada grupo conserva entradas, observaciones nativas, vínculos/IDs e importes en sus JSON. Los seis escenarios de patch quedan UNRUN por el criterio 13. [coverage.json](evidence/frappe-core/coverage.json) impide conservar PASS con casos ausentes o evidencia anterior a la corrección.",
    "",
    "| Criterio | Estado | Evidencia reproducible |",
    "| --- | --- | --- |",
]
for c in criteria:
    rows.append(
        f"| {c['criterion']}. {c['name']} | {c['status']} | "
        + ", ".join(
            f"[{Path(e).name}]({str(Path(e).relative_to('reports'))})"
            for e in c["evidence"]
        )
        + " |"
    )
rows += ["", "## Corrección de cobertura — revisión 2", "",
         "Contrato compartido: [coverage-required.json](../fixtures/ccm-core-v1/coverage-required.json). El oráculo económico y los bytes de los fixtures anteriores se conservan.", "",
         "| Grupo obligatorio | Estado | Comprobación adicional |",
         "| --- | --- | --- |"]
corrections = {
    "AUDIT01-03-NATIVE": "Motivo y JSON antes/después útiles; secuencia de estados, montos, notas y vínculos nativos de compras/caja/tasa/banco; inmutabilidad.",
    "STATE-UNKNOWN-ATOMIC": "Estado desconocido por API y Select nativo: rechazo, snapshot de efectos sin cambios.",
    "STATE-DELIVERY-WITHOUT-ACCEPTANCE": "STORE/WEB desde NEW/REVIEWED y WEB saltando PREPARING: 409 sin efectos.",
    "STATE-WEB-NO-GUIDE": "PREPARING→SHIPPED sin guía: 422, sin salida, factura, pago o evento nuevo.",
    "STATE-CANCEL-BEFORE-HANDOVER": "Cancelaciones APPROVED STORE/WEB y PREPARING WEB: SO nativo cancelado, stock intacto, sin factura/entrega/pago; motivo y antes/después exactos.",
    "MCP01-06-STDIO": "Equivalencia completa API/MCP en seis rutas; creaciones y replays en ambos sentidos con los mismos IDs. Metadata excluida y replay verificado por separado.",
    "MCP-FORBIDDEN-CRITICAL-ACTIONS": "Ocho negativas en objetos elegibles: tool -32602 y RPC 403 para aprobación, entrega/despacho, liquidación, caja, tasa y banco.",
    "MCP-DENIALS-NATIVE-EFFECTS-AUDIT": "Snapshots nativos inalterados, ocho auditorías de denegación y ausencia de auditorías/eventos de éxito.",
    "IDEM04-EVENTS-RECOVERY": "Éxito antes de reiniciar consumidor; efecto persistido; mismos event_id repetidos después: recepciones2 y aplicaciones1.",
}
by_case = {c["case"]: c for c in cases}
for name, description in corrections.items():
    rows.append(f"| {name} | {by_case.get(name, {}).get('status', 'UNRUN')} | {description} |")
rows += [
    "",
    "## Casos económicos y TAX01",
    "",
    "Todos los importes son USD ficticios; impuesto sintético incluido del 10%. Se verificaron facturas, entregas, Stock Ledger Entry, GL Entry y Payment Entry nativos, no asientos calculados externamente. Los JSON guardan los asientos completos por documento.",
    "",
    "| Caso | Total | Ingreso | Pasivo impuesto | Costo | Comisión | Envío | Transferencia Cashea | Resultado contable |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
]
for name, value in json.loads(
    (REPO / "fixtures/ccm-core-v1/oracle.json").read_text()
).items():
    rows.append(
        "| "
        + name
        + " | "
        + " | ".join(
            value[k]
            for k in [
                "gross",
                "revenue",
                "tax",
                "cost",
                "commission",
                "shipping",
                "transfer",
                "accounting_profit",
            ]
        )
        + " |"
    )
rows += [
    "",
    "En cada escenario: stock 5/5/5 y valor 500.00 → 3/4/5 y valor 430.00; una entrega, una factura y dos pagos; saldo final de factura 0.00. TAX01-S/TAX01-W también se ejecutaron concurrentemente y sus reintentos tras reiniciar mantuvieron un solo pasivo de 12.50. El indicador Cashea 58.70/55.25 contiene el impuesto y se distingue del resultado contable 46.20/42.75.",
    "",
    "Caja: USD -2.00, VES +10.00, POS/transferencia 0; pendiente Cashea 125.00 separado del efectivo. Confirmación, rechazo de edición y auditoría inmutable comprobados. Compras: seis límites, cargos/descuento, VES, cambio de aprobación y autoaprobación. Banco: exacto/probable/ambiguo/duplicado/sin pareja, decisiones manuales, signo negativo y 1.000 filas concurrentes sin duplicación.",
    "",
    "## Rendimiento observado",
    "",
    "1000 productos, 100 clientes, 1000 pedidos NEW iniciales, 1000 filas bancarias; semilla 100. Por operación: 20 calentamientos + 1000 muestras seriales. Los IDs por muestra son deterministas; los demás valores de creación son iguales. No se mide replay como creación. HTTP local, dos workers; no se establece SLA de producción.",
    "",
    "| Operación | Muestras | p50 ms | p95 ms | p99 ms | Errores |",
    "| --- | --- | --- | --- | --- | --- |",
]
for op in benchmark.get("operations", []):
    if "operation" in op:
        rows.append(
            "| "
            + op["operation"]
            + " | "
            + " | ".join(str(op[k]) for k in ["samples", "p50", "p95", "p99", "errors"])
            + " |"
        )
rows += [
    "",
    "Tiempos crudos, consultas y tiempo DB por muestra: [benchmark-raw.csv](evidence/frappe-core/benchmark-raw.csv). Recursos y metodología: [benchmark.json](evidence/frappe-core/benchmark.json). El recorder nativo mide dentro del servicio RPC; HTTP/autenticación externa están incluidos solamente en el tiempo extremo a extremo. No se grabaron SQL crudos ni credenciales.",
    "",
    "## Reproducción y cambios propios",
    "",
    "Ejecutar `bash scripts/core-test/run.sh` siguiendo [README](../scripts/core-test/README.md). El runner respalda/restaura únicamente sitios ficticios marcados, carga fixtures por Document APIs, mantiene pruebas independientes y publica comandos/códigos de salida. Regenera evidencia e IDs técnicos, conservando el oráculo.",
    "",
    f"Aplicación: {len(appfiles)} archivos Python/JSON, {app_loc} líneas informativas. Diez DocTypes versionados, campos nativos con Custom Field, Workflow, DocPerm, Property Setter y hooks; SQL de negocio manual: 0. No requiere configuración crítica exclusiva de UI. `bench migrate` sincroniza los modelos y ejecuta `core.setup.install` idempotente; no se añade patch manual ni se altera versions.lock.",
    "",
    "Por venta STORE se usan 5 acciones del servicio; WEB 6. Nativos: un Sales Order, una Delivery Note, una Sales Invoice y dos Payment Entry. Una llamada ERP RPC por acción del adaptador. MCP stdio JSON-RPC ejecutó las mismas seis rutas, usando un actor sin aprobaciones ni movimientos financieros directos.",
    "",
    f"Subconjunto oficial de plataforma: {platform['tests']} tests {platform['status']}; alcance: utilidades unitarias. Los cinco tests de registro/paquete también se ejecutan en el runner. Los grupos de negocio son integración real sobre MariaDB/Redis, incluidos HTTP, permisos y concurrencia. No se presenta esto como la suite completa upstream ni como regresión posterior a un patch.",
    "",
    "Suites oficiales de servidor sobre sitios vacíos con fixtures oficiales: "
    + "; ".join(f"{r['app']}: {r['status']}, {r['actual_tests_run']} realmente ejecutadas / {r['discovered_test_count']} descubiertas" for r in official.get('results', []))
    + ". Comandos, resultados por ID, fallos y omisiones: [frappe-official-suites.md](frappe-official-suites.md). Los registros JUnit incluyen errores de fixtures/subtests y no se usan para inflar la cantidad real. Estas suites de baseline no acreditan las seis pruebas posteriores al patch.",
    "",
    f"El sitio de reproducción separado restauró el checkpoint y repitió {repro.get('replayed_case_counts', {}).get('business', 'UNRUN')} grupos de negocio y {repro.get('replayed_case_counts', {}).get('finance', 'UNRUN')} de finanzas sin modificar el sitio medido. Credenciales, encryption_key, dumps y logs completos permanecen privados, fuera del repositorio. Solo se publican hashes/metadatos y evidencias ficticias.",
    "",
    "## Limitaciones, diagnóstico y resolución",
    "",
    "1. **Criterio 13 BLOCKED; sus seis escenarios UNRUN.** Los tags oficiales de Frappe y ERPNext solo ofrecen 16.36.0 y 16.36.1 en la serie fijada. Ver comandos/SHAs/códigos en [patch.json](evidence/frappe-core/patch.json). No se inventa un patch ni se fuerza otra minor. Para resolver: (1) consultar nuevos tags oficiales compatibles de ambos proyectos; (2) fijar objetivo/SHAs y compatibilidad; (3) definir backup, copia, migración, regresión y rollback; (4) ejecutar únicamente el cambio autorizado; (5) comprobar suites y restauración. Una propuesta para otra minor requiere plan separado y aprobación previa. El baseline actual no cuenta como esas regresiones; no hay aprobación 14/14.",
    "",
    "2. **Standard Buying resuelto; resultados oficiales separados.** Se prepararon sitios vacíos sin Cencomun, con fixtures oficiales y un Bench copiado para aislar tests de comandos. No se cambió la lista LAB ni el oráculo. Las suites oficiales conservan sus FAIL/BLOCKED/UNRUN reales, cantidades e IDs en [frappe-official-suites.md](frappe-official-suites.md); los cuatro unitarios históricos no las sustituyen. `pip check` detecta incompatibilidades preexistentes de requests/oauthlib que se documentan sin cambiar pins. Diagnóstico y repetición paso a paso: [README oficial](../scripts/official-tests/README.md). Esta evidencia no sustituye ni aprueba el criterio 13.",
    "",
    "3. **Alcance técnico del laboratorio.** Cashea y consumidor de eventos son simuladores locales; entrega al menos una vez con deduplicación, no integración real. Serial verifica búsqueda del registro nativo; no seguimiento físico por serial. No se prueba localización fiscal venezolana, remisión del impuesto, devoluciones, combos a cero, integración MRW, producción ni SLA. Las decisiones comerciales aplazadas siguen en el ExecPlan.",
    "",
    "4. **Intervenciones realizadas y preservadas.** Se añadieron Currency VES, grupos hoja, cuentas por defecto, listas nativas y cliente mariadb-dump 11.8.6 con checksum. Se corrigieron el mapeo bruto/neto de Payment Entry, precio/listas obligatorias, scope nativo sin permisos de empresa, auditoría de cierre sin diferencia y traducción de UniqueValidationError a 409. El proxy baseline apuntaba a otro sitio: el adaptador usa 127.0.0.1:8000 con Host ccm-core.test. No se modificó ese proxy. Los intentos fallidos se conservan en `evidence/frappe-core/attempts` y runs; los pasos exactos están en el README.",
    "",
    "5. **Restauración cloud: ejecución separada terminada según el coordinador.** Resultado y evidencia pendientes de incorporación; no se acredita PASS ni se repite esa comprobación aquí. El criterio 14 acredita setup/replay de sitio LAB y mantiene un alcance distinto. El snapshot sigue siendo fcf690dbc58b2b2dcf8d045c49976e3613e804cf; no se repitió Guardar/Publicar. [Procedimiento reproducible](../docs/FRAPPE_CLOUD_RESTORE_CHECK.md): registrar identidad real de tarea, commit/servicios y consultas autenticadas P001, USD50.00 y stock5. Otro sitio local no acredita restauración cloud.",
    "",
    "Versiones efectivas: Frappe/ERPNext 16.36.1, MariaDB 11.8.6, Redis 8.0.2, Python 3.14.0, Node 24.19.0, Bench 5.29.0, Cencomun 0.0.1. Fuente, SHAs, hashes, estados y resultados completos: [summary.json](evidence/frappe-core/summary.json).",
    "",
]
REPORT.write_text("\n".join(rows))
print(
    "Published criterion counts:",
    counts,
    "Core groups:",
    core_count,
    "mandatory approval:",
    summary["mandatory_approved"],
)
