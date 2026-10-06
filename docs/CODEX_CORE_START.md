# ccm-erp-lab-frappe — Core Test autorizado

Usar el checkout existente `/workspace/cencomun-erp-lab` en
`lab/frappe-baseline`. Cada tarea cloud ya está aislada: no crear worktrees salvo
petición explícita. Leer `docs/CODEX_CLOUD_SETUP.md`, `AGENTS.md`,
`labs/frappe/AGENTS.md`, `versions.lock`, `docs/PROJECT_CHARTER.md`,
`docs/CORE_TEST_SPEC.md`, `docs/ACCEPTANCE_CRITERIA.md`,
`docs/COMPARISON_PROTOCOL.md`, `tasks/100-ccm-core-test.md` y
`scripts/core-test/README.md` antes de trabajar.

El usuario autorizó implementar y ejecutar el ExecPlan corregido, incluido
TAX01, exclusivamente en Frappe y con datos ficticios. Preservar sus respuestas,
el plan y el oráculo común; no reabrir el cuestionario comercial. Esta
autorización sustituye la restricción anterior de hacer solo onboarding sin
Core Test. No modificar producción, main, la rama de Axelor ni código upstream.
Mantener las versiones fijadas y usar extensiones soportadas de la app Cencomun.
La comparación futura debe ejecutar el mismo manifiesto en Axelor; esta tarea
no afirma paridad entre ambos ERP.

Continuación técnica autorizada desde fcf690d: ejecutar suites oficiales con
fixtures upstream en sitios/Bench aislados, conservar sus conteos reales y
fallos, repetir Cencomun afectado y documentar verificación cloud. El usuario
confirmó que el catálogo ya conserva ese commit: **no repetir Guardar/Publicar**.
La comprobación de retención se hará en una tarea cloud nueva siguiendo
`docs/FRAPPE_CLOUD_RESTORE_CHECK.md`; no reconstruir antes de verificar.

## Estado verificado y artefactos

Leer `reports/frappe-core-test.md` y `reports/evidence/frappe-core/summary.json`:
34 grupos PASS, 0 FAIL; 13/14 criterios PASS, 0 FAIL y criterio 13 BLOCKED.
Los seis escenarios dependientes del patch quedan UNRUN. TAX01-S y TAX01-W
incluyen impuesto sintético del 10% dentro del precio, comisiones sobre el
total, separación contable nativa de ingreso/impuesto/gastos, concurrencia y
replay después de reiniciar. La reproducción en otro sitio restaurado repitió
18 grupos nativos de negocio/finanzas. Cuatro tests oficiales de utilidades
unitarias y cinco tests de registro/paquete pasaron; no son la suite completa
upstream. El wheel contiene los diez DocTypes JSON versionados y verificados.
La revisión 2 exige motivos y JSON antes/después semánticos, rechazos de estados,
cancelaciones nativas, ocho negativas MCP sobre objetos elegibles, equivalencia
completa API/MCP y éxito de evento antes de reiniciar y reentregar. El contrato
coverage-required.json impide PASS con casos obligatorios ausentes o antiguos.
Siete tests de clasificación verifican FAIL/BLOCKED/UNRUN frente a cobertura.

El baseline técnico anterior conserva su evidencia histórica de 39 checks en
`reports/frappe-integral.md`; no sumar esos checks a los grupos del Core Test.
El PR de revisión es https://github.com/guilmondt/cencomun-erp-lab/pull/4 y sigue
como borrador sin merge. Las evidencias de intentos y runs previos se conservan;
los resultados finales son los archivos del directorio raíz `frappe-core`.

Entradas y oráculo: `fixtures/ccm-core-v1/manifest.json` con SHA256 por archivo.
No cambiar los resultados para favorecer una plataforma. Los IDs nativos se
normalizan mediante mappings; los importes, cantidades, roles y estados
funcionales deben coincidir. Los datos y reglas sintéticos LAB no constituyen
políticas reales de Cencomun.

## Runtime retenido y versiones

Debian 13 amd64, sin root ni Docker. Runtime privado:
`/workspace/.local/frappe-integral`. Python 3.14.0, Node 24.19.0,
Bench 5.29.0, Yarn 1.22.22, Frappe/ERPNext 16.36.1, Cencomun 0.0.1,
MariaDB 11.8.6, Redis 8.0.2 y Nginx 1.26.3. Leer SHAs y locks en el repositorio;
no actualizar silenciosamente. Los checkouts upstream y los caches Git de
uv/Yarn son dependencias, no otros proyectos seleccionados.

Sitios ficticios: baseline `ccm-frappe.test`; Core `ccm-core.test`, DB
`ccm_core_lab`; reproducción `ccm-core-recovery.test`, DB `ccm_core_recovery`.
Los sitios Core están marcados y aislados. Los servicios son MariaDB loopback
3307, Redis cache 13000/queue 11000, Gunicorn 8000, Nginx 8080, worker y Socket.IO
por socket local. El adaptador Core escucha en 8090 y el consumidor ficticio en
8091. El proxy baseline 8080 sigue fijado a `ccm-frappe.test`; Core usa 8000 con
`Host: ccm-core.test`. No cambiar ese proxy para probar Core.

## Inicio conservando los datos

Los procesos no sobreviven necesariamente a publicación/restauración cloud.
Desde el checkout:

```bash
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
python scripts/frappe-integral/services.py start
python scripts/core-test/http_services.py start
python scripts/frappe-integral/services.py status
"$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/readiness.py
```

El probe verifica una lectura autenticada: producto P001 por el adaptador,
identificador, precio y stock coincidentes con registros nativos, flag LAB
activo y medición desactivada. Un PID o puerto abierto no demuestra preparación.
No repetir automáticamente suites que crean pedidos o restauran sitios.
Si falta el runtime, ejecutar el install_script guardado o
`bash scripts/frappe-integral/install.sh` y preparar las dependencias Core.
Si falta el sitio/fixture Core, ejecutar el runner completo autorizado.

Para repetir la evaluación completa desde su estado inicial ficticio:

```bash
cd /workspace/cencomun-erp-lab
bash scripts/core-test/run.sh
```

Este runner respalda el estado previo y restaura solo el laboratorio marcado
desde un checkpoint inicial verificado. Instala dependencias de tests fijadas,
migra, carga fixtures, ejecuta pruebas independientes, recuperación y benchmark,
construye el wheel y publica evidencias. Nunca restaura/elimina el baseline.
Antes de usarlo revisar el README y confirmar que el objetivo es repetir la
evaluación, porque reemplaza los datos ficticios Core. Una salida cero no
equivale a 14/14: revisar siempre las matrices PASS/FAIL/BLOCKED/UNRUN.

Configuración crítica versionada: diez DocTypes, hooks, Custom Field, Workflow,
DocPerm y Property Setter por `core.setup.install` idempotente y `bench migrate`.
El sitio Core tiene `ccm_lab_enabled=1`; la medición de consultas se desactiva al
final (`ccm_measure_queries=0`). MCP stdio ofrece las mismas seis operaciones,
sin aprobación ni escritura financiera directa. No hay consumidores externos.

## Credenciales y resolución de problemas

Contraseñas, API keys, encryption_key, dumps, checkpoint y logs completos quedan
privados fuera de Git. Usar los archivos privados del harness; nunca mostrar
valores, entornos completos, headers ni logs sin sanitizar. No hacen falta
secretos de producción ni nuevas credenciales GitHub: usar la autenticación
inyectada existente. Preservar TLS, firmas de paquetes y checksums. La red
mantiene el preset de paquetes y api.github.com; no se amplía por defecto.

Si hay un problema: explicar comando fallido, causa comprobada e impacto; dar
pasos numerados de resolución y el comando de verificación. Consultar los
diagnósticos de `scripts/core-test/README.md` y `reports/frappe-core-test.md`.
Continuar pruebas independientes ante bloqueos; no convertir BLOCKED/UNRUN en
PASS ni modificar el oráculo para superar una limitación.

Criterio 13: los tags oficiales de Frappe y ERPNext siguen sin patch posterior
compatible dentro de 16.36. Conservar BLOCKED y seis escenarios UNRUN. Otra
minor requiere plan separado con SHAs, compatibilidad, backup, migración,
regresión y rollback, y aprobación antes de ejecutarlo. No se cambiaron pins.
Standard Buying se resuelve con sitios vacíos y fixtures oficiales, sin cambiar
el oráculo LAB. Leer `reports/frappe-official-suites.md` y
`scripts/official-tests/README.md`: suites completas, conteos reales, fallos,
errores de fixtures/subtests, resultados ausentes e intentos previos. Cuatro unitarios
históricos no representan esas suites. No se prueban Cashea/MRW reales, fiscalidad
venezolana, seguimiento físico serial, producción ni SLA. La reproducción
comprobada usa otro sitio en la misma máquina. La comprobación de una tarea cloud
nueva terminó según el coordinador; sus resultados/evidencias siguen pendientes
de incorporación. No volver a ejecutarla aquí ni atribuirle PASS sin evidencia.

Usar la skill cloud-environment-onboarding:setup para cambios de entorno.
Esta continuación no solicita ni modifica el borrador del entorno guardado;
la instrucción explícita del usuario es no repetir Guardar/Publicar. El snapshot
fcf690d y el commit posterior de preparación son identidades distintas: verificar
primero el HEAD retenido, leer el instrumento nuevo desde un SHA revisado sin
cambiar ese checkout, y conservar la evidencia de la nueva tarea cloud.
