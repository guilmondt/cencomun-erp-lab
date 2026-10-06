# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37418693317](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37418693317),
commit `fc6846307688fbc125caa5b7de49d3243d4b21e9`, **FAILURE**.
La preparación del catálogo revierte por AddressTemplate incompleto (B25).
No se alcanzaron pagos ni se demostraron gates económicos en esta repetición.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Causa observada |
| --- | --- | --- | --- |
| CO00, primero | FAIL | 4.941 s | StringTemplates recibe plantilla de línea null al preparar dirección |
| TAX01-W, segundo | FAIL | 0.434 s | Misma frontera de preparación |

AddressBaseRepository.save renderiza addressL2Str–addressL6Str además del
formato completo; el fixture sólo llenaba templateStr. La preparación atómica
se revierte y no confirma catálogo ni nueva entrada inicial. B25 documenta causa,
impacto y pasos antes de la corrección: completar las cinco plantillas con campos
nativos de Address, conservando renderer, repositorio y validaciones.
Compilación local comprobada; repetición ERP pendiente.

En CI9 se verificaron Sequence tras preparación confirmada, draft oficial,
entrada inicial REALIZED y stock 5/5/5. No se demostraron aún stock final 3/4/5,
costo 70, IVA ni liquidación. Un gate administrativo PASS seguirá siendo
parcial hasta ejecutar roles, estados, rechazos, atomicidad e idempotencia.

## Casos independientes y paridad FX

- PROD FAIL (0.449 s), BANK-BOOK FAIL (0.334 s): mismo error nativo al preparar.
- SEARCH FAIL (0.044 s): login 401; el usuario del fixture no confirmó.
  Diagnóstico de búsqueda del lector pendiente, sin ampliar permisos.
- FX: runner reporta FAIL (0.148 s), `Catalog must commit first`. Su aviso grande
  excede el límite del log; sin ZIP, la matriz secundaria mantiene UNRUN.
  No se reconstruye evidencia completa desde el fragmento.
- Resultados históricos separados en [CI9](evidence/axelor-core/runs/37416107406/coverage.json):
  PROD y BANK-BOOK completos PASS; conversiones 40/41/40.5 y 0.41+0.41=0.82
  parciales PASS. FX completo UNRUN porque ese CI no creó cuatro pagos.
- La implementación actual exige tres facturas USD y cuatro InvoicePayment VES
  mediante InvoiceGenerator y servicios nativos de líneas, validación, términos,
  asientos y conciliación. Fecha, tasa, importe, efectos USD y saldo cero se
  verifican desde peticiones nuevas después del commit. **Cuatro pagos aún no
  demostrados en ERP.** El agregado rechaza tasas/cálculos solos, pagos ausentes,
  asientos draft, fechas incorrectas y deuda pendiente.
- B25 limita el resumen FX sin modificar el JSON completo del artefacto. Una
  regresión reproduce el error grande y exige recuperación de FAIL, sin PASS.

Impedimentos, pasos numerados y verificación:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md), B19–B25.

## Matriz de 34 grupos — ejecución actual, evidencia secundaria íntegra

**PASS 0 / FAIL 5 / BLOCKED 0 / UNRUN 29**.
Runner: 6 FAIL / 28 UNRUN; diferencia por aviso FX incompleto. No se mezclan
parciales históricos, tests unitarios o resultados supuestos.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | ---: | --- | --- |
| CO00-NATIVE | 1 | FAIL | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | FAIL | No |
| PROD01-04 | 1 | FAIL | No |
| VAL01-04 | 1 | UNRUN | No |
| STATE01-04 | 1 | UNRUN | No |
| INV01-03-INSUFFICIENT | 1 | UNRUN | No |
| FX01-03-MONEY01-03 | 1 | UNRUN | No |
| PO01-09-NATIVE | 1 | UNRUN | No |
| PO07-09-REVISION-SELF | 1 | UNRUN | No |
| CASH00-06-NATIVE | 1 | UNRUN | No |
| BANK-BOOK-FIXTURE | 1 | FAIL | No |
| BANK01-05-NATIVE | 1 | UNRUN | No |
| API01-06-SIX-ROUTES | 1 | UNRUN | No |
| IDEM01-02-CREATE-CONCURRENT | 1 | UNRUN | No |
| PERM-API-NATIVE | 1 | UNRUN | No |
| CASH04-06-HTTP-IMMUTABLE | 1 | UNRUN | No |
| SEARCH01-04-NATIVE | 1 | FAIL | No |
| TAX02-04-IDEM-CONCURRENT | 1 | UNRUN | No |
| BANK-CONCURRENT-1000 | 1 | UNRUN | No |
| MCP01-06-STDIO | 2 | UNRUN | No |
| IDEM03-LOST-RESTART | 1 | UNRUN | No |
| IDEM04-EVENTS-RECOVERY | 2 | UNRUN | No |
| FIXTURE-HASH-NATIVE-EXPORT | 1 | UNRUN | No |
| AUDIT01-03-NATIVE | 2 | UNRUN | No |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | 1 | UNRUN | No |
| SUPPORTED-CONFIGURATION | 1 | UNRUN | No |
| STATE-UNKNOWN-ATOMIC | 2 | UNRUN | No |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | 2 | UNRUN | No |
| STATE-WEB-NO-GUIDE | 2 | UNRUN | No |
| STATE-CANCEL-BEFORE-HANDOVER | 2 | UNRUN | No |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | 2 | UNRUN | No |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | 2 | UNRUN | No |

## 14 criterios — evidencia ejecutada

| Criterio | Estado |
| ---: | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | FAIL |
| 5 | FAIL |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | FAIL |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio 2 deriva del build del mismo commit: suites, WAR, pins y diffs upstream
reales cero. Ningún criterio está preasignado. Benchmark/recovery no se aprueban
por smoke. Criterio 13 BLOCKED por decisión expresa del usuario; seis PATCH UNRUN.

## Métricas y validaciones

- CI: 19 regresiones Python; 2 tests originales + 7 de política + 16 upstream,
  cero errores/fallos/skips según atestación del log.
- Corrección B25 posterior: 20 regresiones PASS; 2+7 locales PASS; compilación
  full-native con locks externos y replay offline estricto PASS, en secuencia.
  Estas pruebas no sustituyen ejecución del ERP.
- Continuación preparada tras iniciar CI 37420752108: 22 regresiones del runner
  PASS; dos tests del callback nativo de dirección PASS sin DB; 2+7 originales
  y compilación full-native offline PASS. SEARCH continúa serial/factura tras
  fallos de cliente; FX continúa las otras fechas tras un pago fallido. El próximo
  CI exigirá los dos tests de callback y conservará los diagnósticos íntegros por
  subcaso en el log. No se transfiere ninguna de estas pruebas a los grupos ERP.
- Readiness inicial 425.60 s; reinicio misma DB 324.47 s; job 19 min 31 s.
  Son timings de smoke, no benchmark de operaciones.
- Runner: 4 CPU / 4 de afinidad,
  Linux-6.17.0-1022-azure-x86_64-with-glibc2.41, disco libre 87100694528 bytes.
- HTTP: `{"administrator": 11, "product_operator": 0, "search_reader": 2, "fx_operator": 0, "fx_manager": 0}`. FX no inicia sesión ni crea pagos.
- p50/p95/p99, 1000 muestras y query/DB timing: UNRUN.
- JAR propio sin com.axelor.*, pins/lock originales y upstream sin diferencias.
  Perfiles Gradle ejecutados secuencialmente en este checkout compartido.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR: `1f5c787f09e6068982650188e464d7ac056a26b3f0825ae3d7a93ffbc779955b`.

## Evidencia y continuidad

[coverage.json](evidence/axelor-core/runs/37418693317/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37418693317/build-evidence.json),
[runtime-metrics.json](evidence/axelor-core/runs/37418693317/runtime-metrics.json),
[gates, smokes, procedencia y hashes](evidence/axelor-core/runs/37418693317/evidence-source.json).
Fuente secundaria: JSON completo del log. ZIP 11393176285 bloqueado con Forbidden
por productionresultssa18.blob.core.windows.net, un intento, sin ampliar/publicar red.
Log recuperable: `/workspace/ccm-axelor-runtime/ci-evidence/37418693317.log`.

Se continúa la repetición autorizada de gates primero y casos independientes
después. No hay PR, merge, despliegue, cambio de main/Frappe/upstream/pins ni
cierre de comparación. Arranque guardado sólo como borrador; no se publica red pendiente.
