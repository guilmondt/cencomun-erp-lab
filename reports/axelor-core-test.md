# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 archivos de fixtures byte a byte, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Trabajo exclusivo en `lab/axelor-baseline`.

Último CI finalizado: [37407761697](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37407761697),
commit `d1b3930486b7be0480ae394a506e149e700f493c`, **FAILURE**.
La preparación falló por crear clientes asociados a la compañía antes de su
configuración contable. La corrección conserva el repositorio nativo y cambia
sólo ese orden del fixture; compilación local comprobada, nueva repetición CI pendiente.

## Resultados económicos parciales

| Gate, administrador real | Resultado del último run | Tiempo | Etapa |
| --- | --- | --- | --- |
| CO00, primero | FAIL | 4.030 s | Preparación de catálogo/configuración |
| TAX01-W, segundo | FAIL | 0.222 s | Misma preparación |

Estos resultados son parciales. Incluso un gate económico PASS como administrador no
sustituye roles, estados, rechazos, atomicidad e idempotencia del grupo completo.
Todavía no se demuestran stock final 3/4/5, costo de ventas 70, impuestos y liquidación.

## Correcciones y límites observados

1. El ejecutor volvió a responder. Logs recuperados en
   `/workspace/ccm-axelor-runtime/ci-evidence`; la rama remota conserva los commits.
2. `fetch-depth: 0`, guard de commit/blob `e0190090...` y comparación estricta
   de pins real corrigieron finalize. El criterio 2 sí se deriva de pruebas ejecutadas.
3. Run 37405935889 confirmó las doce secuencias y versiones persistidas entre
   peticiones; el contador nativo inStockMove pasó de 1 a 2 y no se repitió
   NoResultException. Se verificó esa frontera; no el resultado económico completo.
4. Ese run detectó después una referencia StockMove separada del contexto tras plan.
   Se conservan los resultados de save y se administran de nuevo siguiendo el
   JpaModelHelper oficial; sin estados manuales ni commits financieros añadidos.
   El run nuevo falló antes de stock, por lo que esta corrección aún requiere repetición.
5. Se corrige B08 configurando la contabilidad antes de guardar clientes con companySet.
   El fallo se documentó antes de ampliar alcance, con fuente nativa y pasos de solución.
6. PROD01-04 se intentó y falló en preparación (0.211 s). SEARCH se intentó y
   recibió 401 porque esa preparación no creó su lector (0.044 s). No se
   transfieren esos resultados a funciones de Axelor que no alcanzaron a probarse.
7. Campos propios de producto con FK Company/Product, generación AOP y permisos
   por compañía; CRUD de operador y consultas de lector reales implementados.
   Aceptación nativa pendiente. El JAR propio no contiene clases com.axelor.*.
8. Se añadió export y aserción del impuesto por cada línea nativa de factura,
   además de los totales. Un test rechaza la distribución equivocada aun si la
   cabecera suma correctamente. Esta nueva aserción espera ejecución en CI.
9. Upgrade: criterio 13 BLOCKED por instrucción expresa; seis casos PATCH UNRUN.
   Preset restringido intacto: dominios 19/1 siguen en borrador; 4/14 bloqueados
   registrados sin añadirlos. Los logs completos sí se recuperaron por la ruta de gh run.

Causa, impacto, pasos numerados y verificación por impedimento:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md).

## Matriz de los 34 grupos — último CI finalizado

PASS 0; FAIL 4; BLOCKED 0; UNRUN 30. Los cuatro grupos intentados no están completos.
Los fallos de preparación pertenecen al caller Cencomun y no prueban incapacidad del ERP.

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
| BANK-BOOK-FIXTURE | 1 | UNRUN | No |
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

## Criterios — derivados de evidencia ejecutada

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

Criterio 2 PASS por commits host/AOS exactos, diffs upstream reales cero,
blob de pins idéntico al baseline, WAR y suites actuales verificados.
El agregador rechaza revisión obsoleta, prueba incompleta o PASS sin evidencia.
Los unit tests no completan grupos nativos sin ejecutar.

## Métricas y pruebas

- Último CI: 2 tests originales + 7 de política + 16 upstream; 0 errores/fallos/skips.
- Correcciones actuales locales: mismos 2+7 tests y 12 regresiones Python PASS.
- Entidades nativas: compilación, JAR por perfil full-stack y replay offline PASS.
- Primer arranque real del último CI: 422.47 s; reinicio de la misma DB: 315.31 s.
- Código de producto y recurso propio cargado en WAR; persistencia/CRUD no demostrados.
- Una tabla propia de perfil con FK/enums; sólo DDL en DB desechable, ningún servicio de producción.
- Benchmark 1000 muestras, query/DB timing y p50/p95/p99: UNRUN. Readiness y tiempos
  de gates no sustituyen ese benchmark. No se infiere hardware comparable.
- Muestras HTTP completas quedan en el artefacto real; no se reconstruyen datos ausentes del log.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR del CI finalizado: `6d29533645fefa89351dfbc18df74ba08ab7505a21a69a5fad2437a3b1163133`.

## Evidencia recuperable y continuación

[coverage.json](evidence/axelor-core/runs/37407761697/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37407761697/build-evidence.json),
[metrics.json](evidence/axelor-core/runs/37407761697/metrics.json), resultados independientes
 y gates en ese directorio. Sólo se extrajeron avisos estructurados completos.
Los fallos de preparación heredados contienen explícitamente la referencia fija
 dentro de su error nativo; se conserva esa procedencia. No se infiere éxito
 de un aviso ausente/truncado. Los exports de secuencias del run anterior
 siguen en `evidence/axelor-core/runs/37405935889`.

Continúa autorizada la ejecución de gates y casos independientes. No hay PR,
merge, despliegue, cambios de main/Frappe/upstream/pins ni cierre de comparación.
