# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37420752108](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37420752108),
commit `f058d21352d73e583c923565c25f754c3ad37e93`, **FAILURE**.
La preparación del catálogo revierte por líneas requeridas de AddressTemplate
sin inicializar (B26). No se ejecutaron pagos ni se demostraron gates económicos
en esta repetición. No se trasladan PASS de producto o banco de otros commits.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Causa observada |
| --- | --- | --- | --- |
| CO00, primero | FAIL | 5.994 s | checkRequiredAddressFields itera addressTemplateLineList null |
| TAX01-W, segundo | FAIL | 0.523 s | Misma preparación nativa incompleta |

El renderer superó el error de plantillas null de CI10, pero no estaba cubierto
el ciclo completo de save. El repositorio oficial renderiza cinco líneas y el
formato, computa fullName, comprueba requeridos mediante MetaField y persiste.
La revisión del importador oficial identifica cinco líneas: floor/postBox
opcionales y streetName/city/zip requeridos. La corrección resuelve metadatos
nativos persistidos, configura esos hijos con el helper oficial y usa campos
modernos Address/City. No hay fullName calculado manualmente ni colección vacía
para eludir validaciones.

El preflight enfocado de CI guarda mediante AddressBaseRepository, inspecciona
IDs de hijos/metadatos y nombres en una petición posterior al commit, repite el
fixture y exige otra lectura idéntica antes de CO00/TAX01-W y del reinicio.
Las pruebas de callbacks se ordenan antes de WAR/launcher; el grafo upstream
puede requerir compilación/frontend y el preflight del ERP requiere WAR/arranque.
**Aceptación del guardado en el ERP real pendiente en esta corrección.** Sólo se
separa la preparación del fixture; no se altera atomicidad de venta, entrega,
factura, liquidación ni rechazos.

En CI9 se verificaron Sequence tras preparación confirmada, draft oficial,
entrada inicial REALIZED y stock 5/5/5. No se demostraron todavía stock final
3/4/5, costo 70, IVA ni liquidación. Un gate administrativo PASS seguirá siendo
parcial hasta ejecutar roles, estados, rechazos, atomicidad e idempotencia.

## Casos independientes y paridad FX

- PROD FAIL (0.441 s), BANK-BOOK FAIL (0.339 s): preparación de dirección revierte.
- SEARCH FAIL (0.046 s): login 401; el usuario del fixture no confirmó.
- FX FAIL (0.063 s): `Catalog must commit first`. El resumen acotado sí contiene
  JSON completo en este CI; el FAIL se conserva, sin reconstruir un PASS.
  No se ejecutó ninguna conversión ni pago en esta repetición.
- Resultados históricos separados en [CI9](evidence/axelor-core/runs/37416107406/coverage.json):
  PROD/BANK-BOOK PASS en ese commit; conversiones 40/41/40.5 y 0.41+0.41=0.82
  parciales PASS. FX completo UNRUN: no había cuatro pagos.
- FX exige tres facturas USD y cuatro InvoicePayment VES, con servicios nativos
  de generación, líneas, validación, términos, asientos y conciliación. Fecha,
  tasa e importe, efectos USD y saldo cero se comprueban en peticiones nuevas
  después del commit. **Cuatro pagos aún no demostrados en ERP.**
- El agregador rechaza cálculos/tasas solos, pagos ausentes, asientos draft,
  fechas incorrectas y deuda pendiente. El runner continúa las otras fechas
  tras un pago fallido; SEARCH continúa serial/factura tras fallos de cliente.
  Estas continuaciones aún requieren repetición del ERP en el nuevo commit.

Impedimentos, pasos numerados y verificación:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md), B19–B27.

## Matriz de 34 grupos — último CI, evidencia secundaria íntegra

**PASS 0 / FAIL 6 / BLOCKED 0 / UNRUN 28**. Coincide con los avisos del runner.
Los parciales históricos y los tests unitarios no aprueban grupos nativos.

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
| FX01-03-MONEY01-03 | 1 | FAIL | No |
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

Criterio 2 deriva de las suites, WAR, pins y diffs upstream reales del mismo
commit. También se rechaza cualquier suite adicional con fallo/error/skip.
No hay PASS preasignados. Un preflight de dirección PASS no aprueba grupos ni
criterios del Core. Benchmark/recovery no se aprueban por smoke. Criterio 13
BLOCKED por decisión expresa del usuario; seis PATCH UNRUN.

## Validaciones locales y límites

- Corrección actual: 24 regresiones Python PASS; ocho tests de callbacks nativos
  PASS (0.696 s), cero fallos/errores/skips. Incluyen metadatos/relaciones,
  colección null y cada campo obligatorio. 2 tests originales + 7 de política
  PASS; compilación/JAR del perfil cloud con lock original y replay offline.
- PostgreSQL 16.15 fijado arrancó y aceptó loopback en el diagnóstico local.
  JPA no llegó al save: tras corregir classpath/listeners según el patrón
  oficial, AppModule exige RequestScoped del contexto HTTP. InitializationError
  real, 1 fallo, guardado/lectura UNRUN. Se usa el preflight dentro del ERP de CI
  sin sustituir scopes ni desactivar auditoría. Docker no prueba full-stack fiable.
- Contenedores/volúmenes propios y configuración privada temporal eliminados;
  credenciales efímeras sin persistencia. Sin cambios de permisos o red.
- [Pruebas y diagnóstico local](evidence/axelor-core/address-preflight-local-20261006/diagnostic.json).
  Logs/fuente JPA recuperables en `/workspace/ccm-axelor-runtime/address-preflight`.
  El test JPA no se incorpora como suite de aceptación ni se cuentan sus
  intentos fallidos como pruebas del ciclo de negocio.
- Compilación/JAR full-native con locks externos estrictos offline PASS (12 s).
  JAR propio sin clases upstream. No equivale a aceptación del ERP.

## Métricas del CI 37420752108

- 20 regresiones Python; suites 2 originales + 7 de política + 16 upstream,
  cero fallos/errores/skips según atestación del log. Ese commit no contenía
  las ocho regresiones ni el preflight enfocado nuevos.
- Readiness inicial 422.53 s; reinicio misma DB 321.31 s; job 18 min 31 s.
  Son timings de smoke, no benchmark de operaciones.
- 4 CPU / afinidad 4, Linux-6.17.0-1022-azure-x86_64-with-glibc2.41,
  disco libre 87098314752 bytes. HTTP: administrador 11, lector 2;
  operador producto/FX y gerente FX 0. No hubo pagos.
- p50/p95/p99, 1000 muestras y timing query/DB: UNRUN.
- JAR propio sin com.axelor.*, pins/lock originales y upstream sin diferencias.
  Perfiles Gradle ejecutados secuencialmente en el checkout compartido.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR: `7b1d75e9c3a823bb92b7051c68046a66a0b2ce74a4d369c867bde49452ee3980`.

## Evidencia y continuidad

[coverage.json](evidence/axelor-core/runs/37420752108/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37420752108/build-evidence.json),
[runtime-metrics.json](evidence/axelor-core/runs/37420752108/runtime-metrics.json),
[gates, smokes, procedencia y hashes](evidence/axelor-core/runs/37420752108/evidence-source.json).
Fuente secundaria: JSON completo del log. ZIP 11393546981 bloqueado con Forbidden
por productionresultssa18.blob.core.windows.net, un intento, sin ampliar/publicar red.
Log recuperable: `/workspace/ccm-axelor-runtime/ci-evidence/37420752108.log`.

Se continúa la ejecución autorizada tras el preflight estrecho. No hay PR,
merge, despliegue, cambio de main/Frappe/upstream/pins ni cierre de comparación.
Arranque guardado sólo como borrador; no se publica red pendiente.
