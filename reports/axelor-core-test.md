# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 archivos de fixtures byte a byte, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37411893961](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37411893961),
commit `8e6cafd2c89899d3c9ea8216f6b8d7a6f4105773`, **FAILURE**.
Preparación confirmada, doce secuencias visibles e incremento nativo sin NoResultException.
El gate alcanzó el asiento inicial y falló porque el caller reemplazaba una colección
Hibernate con borrado de huérfanos. Ambos usuarios LAB ya inician sesión realmente.
Los independientes expusieron permisos con parámetros incompatibles, paginación
invertida y journal sin cuentas autorizadas. B11–B14 documentan causas/pasos.
Se corrigen estos cuatro defectos conservando controles y transacciones; la nueva
repetición ERP está pendiente. Compilación/tests locales comprobados.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Evidencia |
| --- | --- | --- | --- |
| CO00, primero | BLOCKED | 6.822 s | PLANNED=2 en fase transitoria; rollback sin stock ni efectos financieros |
| TAX01-W, segundo | BLOCKED | 0.766 s | Mismo error de colección contable; rollback completo del fixture |

No se demuestran aún stock final 3/4/5, costo de ventas 70, impuestos y liquidación.
Un futuro gate PASS como admin seguirá siendo parcial: roles, estados, rechazos,
atomicidad e idempotencia requieren sus propias pruebas antes de completar el grupo.

## Correcciones e independientes

1. Ejecutor recuperado; historial completo y guard del commit/blob base corrigen
   finalize conservando la comparación estricta con `e0190090...:versions.lock`.
2. Fuente Sequence fijada y repetición confirman doce secuencias/versiones visibles
   entre peticiones e incremento nativo aislado. No volvió NoResultException.
   Separación sólo del fixture: venta/entrega/factura/costo/liquidación conservan
   una transacción conjunta. No se sustituyó la numeración del ERP.
3. Conservar resultados de save y volver a administrar StockMove corrigió su
   estado antiguo: PLANNED=2 real fue observado en el nuevo run. Ahora se
   recargan también compañía/cliente/almacén antes de usar sus relaciones lazy.
4. Configurar contabilidad antes de clientes corrigió B08. El repositorio de
   Partner mantiene su inicialización y validaciones de situación contable.
5. B09 (referencias Currency) y B10 (usuarios bloqueados) dejaron de reproducirse.
   Lectura nueva confirmó perfiles y usuarios activos/no bloqueados, roles y matcher;
   operador y lector iniciaron sesión. PROD (1.440 s) falló al comparar Long con Company.
   SEARCH (0.237 s) rechazó otra compañía con 403, pero saltó los resultados por
   Query.fetch(offset,size). Se corrigen parámetros ID y orden fetch(size,offset).
6. Campos de producto propios con FK nativos Company/Product, enums, tracking
   y permisos por compañía. La prueba exige CRUD de operador real y búsquedas
   del lector real; la factura consultada depende del CO00 nativo.
7. Export/aserción por línea de factura añadido: cabecera correcta con impuesto
   mal repartido falla. Todavía no se alcanzó esa aserción en el ERP.
8. BANK-BOOK-FIXTURE se ejecutó (0.419 s) y falló por cuentas no autorizadas en
   CCM-BOOK. Se configura sólo BANK/AR, manteniendo validación nativa. Apertura,
   ventas/costo/cobros/liquidación reciben sus conjuntos concretos. El caller de
   Move conserva la colección administrada usando addMoveLineListItem. Las cuatro
   correcciones compiladas necesitan repetición ERP; el grupo sigue FAIL.
9. Criterio 13 BLOCKED por instrucción expresa; seis PATCH UNRUN. No hay upgrade.
   Red restringida intacta; ampliaciones pendientes sin publicar. El artefacto
   completo del nuevo run sí se descargó sin añadir dominios.

Causa, impacto, pasos numerados y verificación por impedimento:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md).

## Matriz de 34 grupos — último CI finalizado

PASS 0; FAIL 3; BLOCKED 2; UNRUN 29. Ningún grupo completo.
Los defectos de preparación/caller no prueban incapacidad económica del ERP.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | ---: | --- | --- |
| CO00-NATIVE | 1 | BLOCKED | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | BLOCKED | No |
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

## 14 criterios — evidencia real

| Criterio | Estado |
| ---: | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | BLOCKED |
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

Criterio 2 PASS exige host/AOS exactos, diffs upstream reales cero, blob de
pins idéntico al baseline, WAR y suites del mismo run. El agregador rechaza
revisión obsoleta, prueba incompleta o PASS sin evidencia. Los unit tests no
completan grupos nativos sin ejecutar.

## Métricas y validaciones

- Último CI: 2 originales + 7 de política + 16 upstream; 0 fallos/errores/skips,
  y 14 regresiones Python de ese commit. Correcciones locales actuales: 14
  regresiones Python, los mismos 2+7 tests, compilación full-stack y replay offline PASS.
- Readiness inicial: 419.50 s; reinicio de la misma DB: 318.48 s.
- Job completo: 18 min 24 s, incluyendo build, arranque, pruebas y reinicio.
  No equivale a un benchmark de operaciones ni a tiempos por tarea Gradle.
- Runner observado: 4 CPU visibles/4 de afinidad;
  plataforma `Linux-6.17.0-1022-azure-x86_64-with-glibc2.41`; disco libre 87099195392 bytes.
- HTTP Core medido: 15 llamadas del admin, 4 del operador y 5 del lector. Incluye
  login y preparación; los fallos no se convierten en latencias de una acción completada.
- p50/p95/p99, 1000 muestras y query/DB timing: UNRUN. No se infieren de readiness.
- Esquema propio: un perfil de producto con FK/enums, sólo en la DB desechable.
  El artefacto propio no contiene clases com.axelor.*; pins y lock original intactos.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR del último run: `1aa4459c3641ceb4117f4ddbdb627f1f659e293157a60fb4dc2f18a5da579e3e`.

## Evidencia y continuación

[coverage.json](evidence/axelor-core/runs/37411893961/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37411893961/build-evidence.json),
[metrics.json](evidence/axelor-core/runs/37411893961/metrics.json), XML de las tres
suites, preparación, exports/gates, independientes, smoke y procedencia
con hashes en [evidence-source.json](evidence/axelor-core/runs/37411893961/evidence-source.json).
Son archivos reales del artefacto 11390001620; los derivados están etiquetados.
ZIP completo recuperable en `/workspace/ccm-axelor-runtime/ci-evidence/37411893961-artifact`.
Los resultados históricos se conservan aparte y no sustituyen la repetición nueva.

Continúa autorizada la ejecución de gates y casos independientes. No hay PR,
merge, despliegue, modificación de main/Frappe/upstream/pins ni cierre de comparación.
