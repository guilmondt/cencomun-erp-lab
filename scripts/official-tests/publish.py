"""Publish official server-suite evidence separately from the Core Test oracle."""

import collections
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from run import PRIVATE, REPO, ROOT, OUT, parse_results, redact


def sanitize(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    return value


def main():
    cloud_path = REPO / 'reports/evidence/frappe-cloud/restoration-fcf690d-external.json'
    cloud = json.loads(cloud_path.read_text()) if cloud_path.exists() else {}
    cloud_status = cloud.get('resultado', 'BLOCKED')
    attempts = []
    for path in sorted(OUT.glob('*-attempt-*.json')):
        data = json.loads(path.read_text())
        if data.get('evidence_valid', True):
            basename = path.stem
            log = PRIVATE / (basename + '.log')
            xml = PRIVATE / (basename + '.xml')
            if log.exists() and not data.get('interrupted'):
                data.update(parse_results(xml.read_text() if xml.exists() else '', log.read_text()))
                if data.get('diagnostic_tail'):
                    data['diagnostic_tail'] = redact('\n'.join(log.read_text().splitlines()[-75:]))
            data = sanitize(data)
            path.write_text(json.dumps(data, indent=2) + '\n')
        attempts.append({**data, 'evidence': str(path.relative_to(REPO))})
    results = []
    for app in ['frappe', 'erpnext']:
        eligible = [a for a in attempts if a['app'] == app and not a.get('module')
                    and a.get('category', 'all') == 'all' and a.get('evidence_valid', True)]
        selected = max(eligible, key=lambda a: a['attempt']) if eligible else None
        discovery = json.loads((OUT / (app + '-discovery.json')).read_text())
        preparation = json.loads((OUT / (app + '-preparation.json')).read_text())
        if selected:
            method_ids = {c['id'].split(' (', 1)[0] for c in selected['cases']
                          if not c['id'].startswith('.')}
            discovered = [i for category in discovery['categories'] for i in category['test_ids']]
            not_observed = [i for i in discovered if i not in method_ids]
            selected['discovered_test_count'] = discovery['discovered_test_count']
            selected['unobserved_test_ids'] = not_observed
            selected['unobserved_test_count'] = len(not_observed)
            selected['count_note'] = ('actual_tests_run is the official Ran N counter, including native skips. '
                'JUnit counts are result events and include fixture errors/subtests; they are not additional tests. '
                'Unobserved methods have no result; interrupted attempts remain UNKNOWN, not inferred as UNRUN/PASS.')
            selected['failure_exception_counts'] = dict(collections.Counter(c.get('exception', '')
                for c in selected['cases'] if c['status'] in ['FAIL', 'ERROR']))
            (OUT / (app + '-latest.json')).write_text(json.dumps(selected, indent=2) + '\n')
            results.append({'app': app, 'status': selected['status'], 'actual_tests_run': selected['actual_tests_run'],
                            'discovered_test_count': selected['discovered_test_count'],
                            'junit_records': selected['junit_records'], 'counts': selected['counts'],
                            'unobserved_test_count': selected['unobserved_test_count'],
                            'evidence': str((OUT / (app + '-latest.json')).relative_to(REPO)),
                            'command': selected['command'], 'exit_code': selected['exit_code'],
                            'site': selected['site'], 'seconds': selected['elapsed_seconds'],
                            'interrupted': selected.get('interrupted', False),
                            'completed_native_category_counts': selected.get('completed_native_category_counts'),
                            'fixture_preparation_status': preparation['status']})
        else:
            results.append({'app': app, 'status': 'UNRUN', 'actual_tests_run': None,
                            'discovered_test_count': discovery['discovered_test_count']})
    check = subprocess.run([str(ROOT / 'bench/env/bin/python'), '-m', 'pip', 'check'],
                           capture_output=True, text=True)
    metadata = {'scope': 'official default server suites on pinned MariaDB; baseline, not post-patch regression',
                'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'results': results, 'pip_check': {'exit_code': check.returncode,
                                                 'output': redact(check.stdout + check.stderr)},
                'pins_changed': False, 'oracle_changed': False,
                'cloud_restore': {'status': cloud_status, 'execution_reported_complete': True,
                                 'provenance': 'External coordinator evidence; not executed by this agent on this instance',
                                 'evidence': str(cloud_path.relative_to(REPO)),
                                 'attribution': 'reports/evidence/frappe-cloud/restoration-fcf690d-attribution.json',
                                 'expected_commit': 'fcf690dbc58b2b2dcf8d045c49976e3613e804cf',
                                 'procedure': 'docs/FRAPPE_CLOUD_RESTORE_CHECK.md'},
                'attempts': [{'app': a['app'], 'attempt': a['attempt'], 'status': a['status'],
                              'module': a.get('module'), 'category': a.get('category', 'all'),
                              'actual_tests_run': a['actual_tests_run'], 'evidence': a['evidence'],
                              'evidence_valid': a.get('evidence_valid', True)} for a in attempts]}
    (OUT / 'summary.json').write_text(json.dumps(metadata, indent=2) + '\n')
    rows = ['# Suites oficiales Frappe / ERPNext 16.36.1', '',
            'Se ejecutan runners, fuentes y fixtures oficiales, sin cambiar el oráculo LAB, pins o validadores. '
            'Este informe distingue descubrimiento, ejecución real y eventos JUnit. '
            'Los cuatro unitarios históricos de utilidades no son estas suites.', '',
            '| Aplicación | Sitio del último intento registrado | Descubiertas | Ejecutadas (Ran N) | Estado | Exit | Segundos | Evidencia |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for result in results:
        rows.append(f"| {result['app']} | {result.get('site','—')} | {result['discovered_test_count']} | "
                    f"{result['actual_tests_run'] if result['actual_tests_run'] is not None else 'desconocidas'} | {result['status']} | "
                    f"{result.get('exit_code') if result.get('exit_code') is not None else '—'} | "
                    f"{result.get('seconds') if result.get('seconds') is not None else '—'} | "
                    f"[{result['app']}-latest.json](evidence/frappe-official/{result['app']}-latest.json) |")
    rows += ['', '| Aplicación | Eventos PASS | FAIL | ERROR | SKIP | Total JUnit | Métodos descubiertos sin resultado |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for result in results:
        counts = result.get('counts', {})
        rows.append('| ' + result['app'] + ' | ' + ' | '.join(str(counts.get(k, '—'))
                    for k in ['PASS', 'FAIL', 'ERROR', 'SKIP']) + f" | {result.get('junit_records','—')} | {result.get('unobserved_test_count','—')} |")
    rows += ['', '**Los eventos JUnit no son el contador real de pruebas.** setUpClass/tearDownClass y subtests '
             'producen registros adicionales; SKIP no aprueba. Los JSON guardan cada ID, excepción y traza '
             'redactada; en intentos interrumpidos los resultados no observados son desconocidos. Un comando interrumpido '
             'no se convierte en suite aprobada.', '', '## Comandos ejecutados', '']
    for result in results:
        if 'command' in result:
            rows += [f"- `{result['command']}`"]
        if result.get('interrupted'):
            rows += ['', f"**{result['app']}: intento interrumpido, BLOCKED.** No existe resumen final. "
                     f"Los resúmenes de categorías completadas son {result['completed_native_category_counts']}; "
                     'no son el conteo completo. Se conserva log/XML privados y no se inventan resultados.', '']
    rows += ['', 'Preparación, repetición por categoría/módulo y diagnóstico paso a paso: '
             '[README](../scripts/official-tests/README.md). Discovery ejecuta cero pruebas. '
             'El bootstrap ERPNext de CI también ejecuta cero: carga fixtures oficiales; su éxito no es '
             'resultado de suite. Frappe usa su hook oficial antes del comando completo. '
             'Los servidores HTTP pertenecen a los sitios explícitos, sin cambiar el proxy baseline.', '',
             '## Colisión Standard Buying', '',
             'Resuelta usando sitios creados vacíos sin Cencomun y bootstrap oficial ERPNext. '
             '[erpnext-preparation.json](evidence/frappe-official/erpnext-preparation.json) comprueba '
             '`Standard Buying` en INR (buying=1, selling=0), ausencia de P001/flag LAB y aplicaciones '
             'oficiales. No se renombra ni altera la lista del oráculo LAB. '
             'El Bench copiado aísla también los tests que cambian configuración global o generan archivos '
             'en las fuentes de prueba; el runtime y fuentes originales Cencomun no se modifican.', '',
             '## Fallos y limitaciones', '',
             f"`pip check` devuelve {check.returncode}: requests 2.34.2 y oauthlib 4.0.0, ya presentes en "
             'el lock inicial, no satisfacen los rangos declarados por Frappe. Se conservan los pins; '
             'cualquier corrección de esos pins necesita una propuesta separada. No se atribuye todo '
             'fallo de suite a esas incompatibilidades sin demostrar la relación.', '']
    for app in ['frappe', 'erpnext']:
        path = OUT / (app + '-latest.json')
        if path.exists():
            result = json.loads(path.read_text())
            rows += [f"### {app}: excepciones observadas", '', '| Excepción | Eventos fallidos |', '| --- | --- |']
            for error, count in sorted(result['failure_exception_counts'].items()):
                rows.append(f'| {error} | {count} |')
    rows += ['', 'Los intentos anteriores se conservan en [summary.json](evidence/frappe-official/summary.json). '
             'El primer ERPNext tuvo una colisión de nombres de evidencia entre procesos concurrentes: '
             'ambos se interrumpieron, sus conteos quedaron desconocidos/no válidos y se repitió con '
             'reserva exclusiva de nombres. Diez tests del harness verifican cero-test, categorías, '
             'subtests/fixtures, concurrencia, recuperación incompleta, assets y redacción; no son tests oficiales. '
             'El intento ERPNext 2 se conserva incompleto tras perder acceso al ejecutor; '
             '[informe de recuperación](frappe-executor-recovery.md).', '',
             'No se ejecutan UI/Cypress, PostgreSQL, SQLite ni migraciones a otra versión. '
             'No se modifican validaciones para aprobar. Para cada excepción nativa: localizar ID/traza, '
             'identificar causa comprobada, corregir únicamente preparación autorizada, repetir módulo '
             'y conservar el fallo anterior; seguir el diagnóstico del README. Un FAIL o UNRUN nunca '
             'se convierte automáticamente en PASS por una prueba de otro alcance.', '',
             '## Core Test, patch y entorno guardado', '',
             'La regresión Cencomun posterior a preparación se publica separadamente en '
             '[frappe-core-test.md](frappe-core-test.md). Las suites oficiales de baseline no cuentan '
             'como regresión después de patch. Los tags oficiales de ambos proyectos siguen ofreciendo '
             'solo v16.36.0/v16.36.1: criterio 13 BLOCKED, seis escenarios UNRUN. No se cambia minor.', '',
             f'La comprobación del entorno guardado tiene resultado **{cloud_status} externo**, aportado por el coordinador '
             'desde una tarea cloud distinta; no fue reejecutada por este agente. '
             '[Evidencia exacta, atribución y límites](frappe-cloud-restoration.md). '
             '[Procedimiento reproducible](../docs/FRAPPE_CLOUD_RESTORE_CHECK.md): snapshot esperado '
             '`fcf690dbc58b2b2dcf8d045c49976e3613e804cf`, servicios retenidos y consulta autenticada '
             'P001, USD 50.00, stock 5 en almacén HTTP, cotejados con APIs nativas. '
             'Esta tarea no repite Guardar/Publicar; otro sitio en esta máquina no acredita restauración cloud.', '']
    (REPO / 'reports/frappe-official-suites.md').write_text('\n'.join(rows))
    print('Official suite report published:', [(r['app'], r['status'], r['actual_tests_run']) for r in results])


if __name__ == '__main__':
    main()
