# Core Test Axelor — ejecución en curso

CI [37453727869](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37453727869),
commit `5660bc7cedc30c910811691c16b0ef1f067068a3`, FAILURE, 39m45s.
**Primaria:26 PASS / 8 FAIL / 0 BLOCKED / 0 UNRUN. Réplica:27 PASS / 7 FAIL.**
Los 34 grupos fueron ejecutados en ambas fases; no se declara terminada la comparación.
Criterios:12 FAIL / 1 PASS / 1 BLOCKED. Actualización aplazada (13); seis escenarios UNRUN.

Fuente: log completo y revisores congelados del SHA; ZIP403 en
`productionresultssa8.blob.core.windows.net`, un intento, red conservada.
[Recibo de procedencia](evidence/axelor-core/runs/37453727869/evidence-source.json).
[Índice de ambas fases](evidence/axelor-core/runs/37453727869/isolated-repeat.json):
22.428bytes, 92 archivos cargados, 60.654.190bytes, todos los SHA256 verificados.
Agregado original de65.662.508bytes archivado completo fuera del árbol Git;
contenido de ambas fases conservado y comprobado igual. Archivo Git máximo5.076.576bytes.
Revisión de empaquetado sin otra ejecución de negocio; repetición FAIL por resultados
distintos entre fases y benchmark aún incompleto. Ver detalles en
[empaquetado](axelor-core-evidence-packaging.md).

Gates admin CO00/TAX01-W PASS en13,626/6,647s: stock3/4/5, valor430,
COGS70, impuesto0/12,50, dos pagos nativos por factura, AR0 y GL ACCOUNTED.
Los cuatro grupos económicos completos PASS incluyen roles, estados, replay y
rollback503; no se sustituyen por estos gates. FX PASS con cuatro pagos reales
y lecturas posteriores al commit, no sólo cálculos. SEARCH PASS con scopes.

65 tests Java ejecutados, sin fallos/errores/skips, WAR del SHA y upstream
limpio comprobados. Criterio2 deriva de esa evidencia. Arranques autenticados
primaria365,16/272,90s y réplica269,96/275,86s; reinicios propios de Java/PG
y restauración aislada ejecutados. Benchmark FAIL antes de muestras por
`CcmBankRow.getReference/0, matches=0`; p50/p95/p99 UNRUN. No se usan timings
de gates/arranque como benchmark.

Hallazgos que se conservan y correcciones acotadas a validar:

1. VAL01-04 y las tres cancelaciones confirmadas siguen FAIL funcional: coste
   negativo aceptado y cancelación rechazada por el ERP. Expectativas intactas.
2. Caja dio FAIL sólo en primaria: las mismas MoveLine nativas llegaron en otro
   orden; confirmar igualdad por ID y estabilizar su export, sin cambiar importes.
3. PERM y AUDIT fallaron porque CRUD AOP devuelve HTTP200, status=-1 y el mensaje
   nativo de autorización. No hubo datos privados ni cambios en los probes
   ejecutados, pero el grupo abortó antes de completar la matriz: seguridad FAIL.
   Identificar causalmente el rechazo de autorización; jamás aceptar cualquier
   status=-1 o error de fixture como denegación. Mantener API de seis rutas403.
4. Concurrencia TAX devolvió un200 y un500 StaleObjectStateException por cada
   pedido. Resolver la frontera de bloqueo/lectura de CcmOrder con mecanismos
   JPA nativos; conservar dos sesiones, efectos únicos, replay y atomicidad.
   Los conteos tributarios dependientes también FAIL; no se rebaja el oráculo.
5. MCP compra devolvió request_rate0 numérico frente a "0" del otro recorrido.
   Fijar serialización del mismo valor nativo en create/replay; comparar todo
   el resultado y sus FK. El grupo permanece FAIL hasta ejecución nueva.
6. Benchmark debe leer reference desde BankStatementLine de CcmBankRow,
   conforme al modelo real; validar esa API y repetir las muestras congeladas.

| Grupo completo | Primaria | Réplica |
| --- | --- | --- |
| CO00-NATIVE | PASS | PASS |
| CO01-NATIVE | PASS | PASS |
| TAX01-S-NATIVE | PASS | PASS |
| TAX01-W-NATIVE | PASS | PASS |
| PROD01-04 | PASS | PASS |
| VAL01-04 | FAIL | FAIL |
| STATE01-04 | PASS | PASS |
| INV01-03-INSUFFICIENT | PASS | PASS |
| FX01-03-MONEY01-03 | PASS | PASS |
| PO01-09-NATIVE | PASS | PASS |
| PO07-09-REVISION-SELF | PASS | PASS |
| CASH00-06-NATIVE | FAIL | PASS |
| BANK-BOOK-FIXTURE | PASS | PASS |
| BANK01-05-NATIVE | PASS | PASS |
| API01-06-SIX-ROUTES | PASS | PASS |
| IDEM01-02-CREATE-CONCURRENT | PASS | PASS |
| PERM-API-NATIVE | FAIL | FAIL |
| CASH04-06-HTTP-IMMUTABLE | PASS | PASS |
| SEARCH01-04-NATIVE | PASS | PASS |
| TAX02-04-IDEM-CONCURRENT | FAIL | FAIL |
| BANK-CONCURRENT-1000 | PASS | PASS |
| MCP01-06-STDIO | FAIL | FAIL |
| IDEM03-LOST-RESTART | PASS | PASS |
| IDEM04-EVENTS-RECOVERY | PASS | PASS |
| FIXTURE-HASH-NATIVE-EXPORT | PASS | PASS |
| AUDIT01-03-NATIVE | FAIL | FAIL |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | FAIL | FAIL |
| SUPPORTED-CONFIGURATION | PASS | PASS |
| STATE-UNKNOWN-ATOMIC | PASS | PASS |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS | PASS |
| STATE-WEB-NO-GUIDE | PASS | PASS |
| STATE-CANCEL-BEFORE-HANDOVER | FAIL | FAIL |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | PASS | PASS |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | PASS | PASS |

| Criterio | Primaria revisada |
| --- | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | FAIL |
| 5 | FAIL |
| 6 | FAIL |
| 7 | FAIL |
| 8 | FAIL |
| 9 | FAIL |
| 10 | FAIL |
| 11 | FAIL |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | FAIL |

Validación local de empaquetado:74Python y checks shell/repositorio PASS.
El índice no aprueba negocio por etiquetas ni por hashes solos: carga todos
los archivos y ejecuta las aserciones anteriores. Las correcciones de ejecución
anteriores requieren una sola siguiente validación CI, sin duplicar jobs.

## Historia — CI34192b3
# Core Test Axelor — ejecución en curso

Último CI revisado: [37448650654](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37448650654), commit `34192b3b7292dc69a31dda7c95014c2683afee2b`, FAILURE.
**18 PASS / 9 FAIL / 1 BLOCKED / 6 UNRUN**. No se declara terminada la comparación.
Fuente secundaria: notices completos del log, revisores congelados del SHA,
`reports/evidence/axelor-core/runs/37448650654/evidence-source.json`.
ZIP bloqueado en productionresultssa16.blob.core.windows.net, un intento;
no se amplió ni publicó la red pendiente.

Compras PO01–09/revisión, caja, conciliación BANK01–05 y 1.000 filas concurrentes
PASS en este commit. Las seis rutas API y creación concurrente PASS. MCP conserva
cuatro lecturas verificadas, pero la comparación completa de creación falla por
escalas decimales distintas del resultado nativo persistido. Los ocho comandos
críticos MCP y sus denegaciones/auditorías nativas PASS; **PERM-API-NATIVE FAIL**,
no hay aprobación completa de seguridad ni CRUD privado en este run.

Gates económicos de administrador CO00/TAX01-W: BLOCKED por una regresión del
módulo: el guard del servicio InvoicePaymentValidate se invoca desde el callback
de InvoicePaymentManagementRepository.save fuera del scope privado. El rollback
real impidió la liquidación. Los cuatro ciclos completos y pagos FX FAIL;
SEARCH quedó BLOCKED sólo en sus subcasos dependientes de factura CO00.
Los PASS del CI anterior se conservan únicamente como historia.

Correcciones preparadas para el próximo CI:

1. Abrir el scope nativo privado también alrededor de NativeAccess.save de entidades
   ERP, después de las políticas del servicio. Conservar guards de llamadas directas,
   roles, compañía, validaciones y atomicidad; repetir pagos, rollback y asientos.
2. Ordenar filas bancarias por identidad nativa y serializar decimales de líneas de
   compra en formato estable. CI19 devolvió HTTP403 y las mismas 1.005 filas después
   de ordenar; su FAIL original no se cambia. Verificar de nuevo toda la matriz,
   CRUD privado, endpoints internos/nativos, lectura autorizada de pedidos y MCP.
3. Ejecutar agrupados impuestos concurrentes, conteos nativos, auditoría semántica
   e inmutabilidad, metadatos, pérdida real de respuesta y reinicio, outbox durable.
   El consumidor SQLite pertenece sólo al consumidor externo, nunca al ERP.
4. Cargar benchmark congelado: 1.000 productos, 100 clientes, 1.000 pedidos NEW,
   1.000 filas bancarias; 20 warmups y 1.000 solicitudes seriales por búsqueda,
   inventario y creación. Contadores JDBC reales de Hibernate por sesión, sin SQL
   ni datos sensibles; excluir autenticación/serialización/hilos de secuencia.
5. Respaldar antes de fixtures Core y restaurar en otra base desechable del runner;
   repetir los 34 grupos y benchmark con el mismo WAR/pins. Dumps y credenciales
   sintéticas quedan privados. No es una actualización ni habilita criterio 13.

Validación local del bloque nuevo: 61 regresiones Python; 22 tests de módulo y
9 de API/modelos/repositorios nativos, 0 fallos/errores/skips; compile/JAR offline.
La primera prueba aislada del repositorio encontró Guice sin inicializar; se usó
el fixture constructor nativo existente y se repitió con éxito. No valida DB.
CI19 ejecutó 62 tests Java sin fallos y arranque/reinicio autenticados en
428,56/354,46 s. Métricas de gates/arranque no sustituyen al benchmark congelado.

| Grupo completo | Estado CI34192b3 |
| --- | --- |
| CO00-NATIVE | FAIL |
| CO01-NATIVE | FAIL |
| TAX01-S-NATIVE | FAIL |
| TAX01-W-NATIVE | FAIL |
| PROD01-04 | PASS |
| VAL01-04 | FAIL |
| STATE01-04 | PASS |
| INV01-03-INSUFFICIENT | PASS |
| FX01-03-MONEY01-03 | FAIL |
| PO01-09-NATIVE | PASS |
| PO07-09-REVISION-SELF | PASS |
| CASH00-06-NATIVE | PASS |
| BANK-BOOK-FIXTURE | PASS |
| BANK01-05-NATIVE | PASS |
| API01-06-SIX-ROUTES | PASS |
| IDEM01-02-CREATE-CONCURRENT | PASS |
| PERM-API-NATIVE | FAIL |
| CASH04-06-HTTP-IMMUTABLE | PASS |
| SEARCH01-04-NATIVE | BLOCKED |
| TAX02-04-IDEM-CONCURRENT | UNRUN |
| BANK-CONCURRENT-1000 | PASS |
| MCP01-06-STDIO | FAIL |
| IDEM03-LOST-RESTART | UNRUN |
| IDEM04-EVENTS-RECOVERY | UNRUN |
| FIXTURE-HASH-NATIVE-EXPORT | PASS |
| AUDIT01-03-NATIVE | UNRUN |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | UNRUN |
| SUPPORTED-CONFIGURATION | UNRUN |
| STATE-UNKNOWN-ATOMIC | PASS |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS |
| STATE-WEB-NO-GUIDE | PASS |
| STATE-CANCEL-BEFORE-HANDOVER | FAIL |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | PASS |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | PASS |

| Criterio | Estado CI34192b3 |
| --- | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | FAIL |
| 5 | FAIL |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | FAIL |
| 10 | FAIL |
| 11 | FAIL |
| 12 | BLOCKED |
| 13 | BLOCKED |
| 14 | UNRUN |

Coste negativo aceptado y las tres cancelaciones confirmadas rechazadas siguen
siendo FAIL funcionales; se conservan expectativas y evidencia causal. Criterio 2
deriva de builds/pins/diffs reales; 13 BLOCKED por actualización aplazada, seis
escenarios UNRUN. Todo lo nuevo requiere ejecución CI del nuevo commit.

## Historia — CI7d9702f

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
34 grupos y 14 criterios, cobertura revisión 2; fixtures/oráculo/pins intactos.

CI [37445387142](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37445387142),
commit `7d9702ffaff6834fbf0dc19bfecc523716e007e9`, FAILURE: **16 PASS / 6 FAIL / 12 UNRUN**.
Son los resultados ejecutados por ese commit. Los cuatro ciclos completos CO00,
CO01, TAX01-S y TAX01-W pasan roles, estados, replay y rollback económico.
La preparación cronológica del fixture corrigió el diagnóstico del run anterior
sin cambiar fechas ni desactivar la validación nativa de facturas.
Gates de administrador: CO00 13.377 s y TAX01-W 6.774 s, stock 3/4/5,
valor 430, COGS 70, impuesto 0/12.50, GL ACCOUNTED, dos pagos y AR cero.
Se conservan aparte del resultado de los grupos completos.

Caja pasa ambos grupos: ocho movimientos fuente con GL nativo, factura pendiente
125 excluida, cierres CS000/CS001, roles, justificación, replay e inmutabilidad.
UNKNOWN-LAB pasa ambos canales con control válido y Mapper/ValueEnum causal.
VAL01-04 sigue FAIL: el ERP realizó y releyó el coste -0.01, igual que el control
30.00; ambos intentos, stacks y snapshots de rollback están conservados antes
de asserts. Las tres cancelaciones confirmadas siguen FAIL funcional, con error
nativo original y expectativa CANCELLED intacta. No se fuerza su aceptación.

Problemas nuevos observados y resolución acotada:

1. Compra PO01: native_gross y usd_base quedaron 0.00 y la aprobación rechazó
   “Positive money with at most two decimals required”. El cómputo de cabecera
   consume priceDiscounted, que seguía cero. Ejecutar primero el servicio nativo
   PurchaseOrderLineService.compute por línea y después computePurchaseOrder.
   Verificar create/request/approve con total 199.99 y los nueve umbrales/cargos.
   PO02/revisión no existía porque el grupo anterior abortó; no se infiere paridad.
2. Banca: preparación rechazó `Bank.setName/1, matches=0`; Bank tampoco tiene bic.
   Usar campos oficiales bankName y code (BIC), manteniendo cuenta BANK-USD-001,
   IBAN público de ejemplo y valores congelados. Verificar preparación/guardado,
   importación, conciliación, negativo y mil filas concurrentes en CI.
3. Seguridad/API/MCP: escrituras de caja/importación/request/revise requieren
   operador; MCP conserva solo compra DRAFT y pedido NEW. Revocar grants privados
   de audit/key/outbox del fixture a lectores/MCP/otros roles; conservar lectura
   de pedidos. Comprobar las identidades reales por seis rutas, servicios internos,
   acciones oficiales y CRUD, compañía ajena, snapshots y auditoría de denegación.
   Interceptores Guice del módulo protegen llamadas directas a servicios críticos;
   scope privado solo durante llamadas Cencomun autorizadas, sin editar upstream.
   **Estos cambios y los seis grupos API/MCP aún no tienen aceptación runtime.**

Validación de ese CI: 56 tests Java, cero fallos/errores/skips, WAR y diffs upstream
cero. Arranque autenticado 377.17 s; reinicio 266.89 s. Criterio 2 deriva de esa
atestación real; los otros criterios derivan de sus grupos. ZIP sa12 bloqueado
por proxy, un intento; evidencia secundaria completa del log, SHA256 y revisor
congelado del mismo commit. No se amplió ni publicó la red pendiente.

| Grupo completo | Estado CI7d9702f |
| --- | --- |
| CO00-NATIVE | PASS |
| CO01-NATIVE | PASS |
| TAX01-S-NATIVE | PASS |
| TAX01-W-NATIVE | PASS |
| PROD01-04 | PASS |
| VAL01-04 | FAIL |
| STATE01-04 | PASS |
| INV01-03-INSUFFICIENT | PASS |
| FX01-03-MONEY01-03 | PASS |
| PO01-09-NATIVE | FAIL |
| PO07-09-REVISION-SELF | FAIL |
| CASH00-06-NATIVE | PASS |
| BANK-BOOK-FIXTURE | PASS |
| BANK01-05-NATIVE | FAIL |
| API01-06-SIX-ROUTES | UNRUN |
| IDEM01-02-CREATE-CONCURRENT | UNRUN |
| PERM-API-NATIVE | UNRUN |
| CASH04-06-HTTP-IMMUTABLE | PASS |
| SEARCH01-04-NATIVE | PASS |
| TAX02-04-IDEM-CONCURRENT | UNRUN |
| BANK-CONCURRENT-1000 | FAIL |
| MCP01-06-STDIO | UNRUN |
| IDEM03-LOST-RESTART | UNRUN |
| IDEM04-EVENTS-RECOVERY | UNRUN |
| FIXTURE-HASH-NATIVE-EXPORT | PASS |
| AUDIT01-03-NATIVE | UNRUN |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | UNRUN |
| SUPPORTED-CONFIGURATION | UNRUN |
| STATE-UNKNOWN-ATOMIC | PASS |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS |
| STATE-WEB-NO-GUIDE | PASS |
| STATE-CANCEL-BEFORE-HANDOVER | FAIL |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | UNRUN |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | UNRUN |

| Criterio | Estado |
| --- | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | FAIL |
| 5 | FAIL |
| 6 | UNRUN |
| 7 | FAIL |
| 8 | FAIL |
| 9 | FAIL |
| 10 | UNRUN |
| 11 | UNRUN |
| 12 | UNRUN |
| 13 | BLOCKED |
| 14 | UNRUN |

Evidencia: [runs/37445387142](evidence/axelor-core/runs/37445387142/).

La ejecución continúa con los grupos restantes; benchmark, recuperación y replay
independiente requieren evidencia propia. Upgrade sigue aplazado por alcance.

## Historial anterior — sin transferir PASS

# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
34 grupos/14 criterios/revisión2, fixtures, oráculo, manifiesto y pins sin cambios.

Último CI [37442873626](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37442873626),
`37f9d28d74e3fee776f13efcecc2e31d27b496a3`, FAILURE: **10 PASS / 6 FAIL / 18 UNRUN**.
Gates administrador: CO00 PASS13.242s y TAX01-W PASS6.242s, mismos efectos nativos
stock3/4/5, valor430, COGS70, GL ACCOUNTED, impuesto0/12.50 y AR0. Siguen separados
de los grupos completos de roles, estados y atomicidad.

UNKNOWN-LAB ya tiene prueba causal: control REVIEWED persistido/releído y revertido,
Mapper.set/ValueEnum.of rechazó el valor inválido, snapshots posteriores iguales,
ambos canales ejecutados. El coste negativo sigue FAIL (aceptado por ERP); su probe
completo se conservará antes de asserts en el próximo commit, junto con el control
válido. Las tres cancelaciones confirmadas siguen FAIL funcionales con expectativa
CANCELLED y error nativo intactos.

Causa observada de los cuatro ciclos: delivery-rollback esperaba503, obtuvo422 en
VentilateState.checkInvoiceDate: “La date de facture ou d'avoir ne peut être antérieure
à la date de la dernière facture ventilée : 2026-10-02”. Actor ccm-operator,
petición/error/stack y ambos snapshots preservados; revisión independiente comprueba
rollback económico sin cambios. Se habían ejecutado pagos FX del día2 antes de estos
pedidos del día1. La corrección mantiene la validación cronológica: preparar tasas
primero y ejecutar los ciclos/caja del día1 antes de contabilizar FX de días2/3.
Fechas, efectos y expectativas intactos; corrección pendiente de repetir ERP.

Próximo bloque incluye seis grupos financieros, servicios/FK nativos, roles,
revisión/self, caja y libro contabilizados, conciliación bancaria, signo negativo,
replay y1000 filas concurrentes. **UNRUN** hasta aceptación CI. Localmente25 Java y
47 regresiones Python pasan; compilación/locks externos/replay offline estrictos
sin diferencias upstream, baseline locks sin cambios. No sustituye CI.

| Grupo completo | Estado del CI37f9d28 |
| --- | --- |
| CO00-NATIVE | FAIL |
| CO01-NATIVE | FAIL |
| TAX01-S-NATIVE | FAIL |
| TAX01-W-NATIVE | FAIL |
| PROD01-04 | PASS |
| VAL01-04 | FAIL |
| STATE01-04 | PASS |
| INV01-03-INSUFFICIENT | PASS |
| FX01-03-MONEY01-03 | PASS |
| PO01-09-NATIVE | UNRUN |
| PO07-09-REVISION-SELF | UNRUN |
| CASH00-06-NATIVE | UNRUN |
| BANK-BOOK-FIXTURE | PASS |
| BANK01-05-NATIVE | UNRUN |
| API01-06-SIX-ROUTES | UNRUN |
| IDEM01-02-CREATE-CONCURRENT | UNRUN |
| PERM-API-NATIVE | UNRUN |
| CASH04-06-HTTP-IMMUTABLE | UNRUN |
| SEARCH01-04-NATIVE | PASS |
| TAX02-04-IDEM-CONCURRENT | UNRUN |
| BANK-CONCURRENT-1000 | UNRUN |
| MCP01-06-STDIO | UNRUN |
| IDEM03-LOST-RESTART | UNRUN |
| IDEM04-EVENTS-RECOVERY | UNRUN |
| FIXTURE-HASH-NATIVE-EXPORT | PASS |
| AUDIT01-03-NATIVE | UNRUN |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | UNRUN |
| SUPPORTED-CONFIGURATION | UNRUN |
| STATE-UNKNOWN-ATOMIC | PASS |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS |
| STATE-WEB-NO-GUIDE | PASS |
| STATE-CANCEL-BEFORE-HANDOVER | FAIL |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | UNRUN |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | UNRUN |

Evidencia completa saneada: [runs/37442873626](evidence/axelor-core/runs/37442873626/).
Log estructurado secundario con SHA y comprobador congelado del mismo commit;
ZIP sa9 bloqueado, un intento, sin ampliación/publicación de red. Java53 pruebas
CI0fallos/errores/skips; criterio2 deriva de suites, WAR, pins y upstreamdiff0.
Arranque359.16s/reinicio269.91s autenticados. Se continúa el ExecPlan, no se cierra
la comparación en la matriz parcial. Ensayo de actualización fuera de este alcance.

## Historial de ejecuciones anteriores (sin transferir resultados)


Comparación **incompleta**, referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
fixtures/oráculo/manifiesto/cobertura revisión2 sin cambios. Rama exclusiva `lab/axelor-baseline`.

Último CI: [37440203758](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37440203758),
commit `80f94067d0454b23711a56514a27bbc7ea96d65f`, **FAILURE**.
Matriz revisada: **9 PASS / 6 FAIL / 19 UNRUN**, sin bloqueos de entorno asignados a grupos.
Los 14 criterios se calculan desde pruebas; actualización separada permanece bloqueada por alcance.

CO00 administrador PASS13.367s; TAX01-W administrador PASS6.671s. Stock3/4/5,
valor430, COGS70, ingresos125, IVA0/12.50, GL ACCOUNTED y AR0 se vuelven a verificar.
No sustituyen los ciclos completos con roles y atomicidad: los cuatro ciclos fallaron
al comprobar delivery-rollback, tras 14/15 comprobaciones exitosas. El helper antiguo
perdió la respuesta al lanzar AssertionError vacío. No se inventa la causa nativa.
El siguiente run conserva petición, actor, HTTP, error/stack y snapshots antes/después
antes de evaluar la aserción, con mensajes específicos.

Hallazgos ejecutados: coste -0.01 aceptado por StockMove nativo (FAIL funcional);
los tres intentos de cancelar pedido confirmado devuelven422 y
“Vous pouvez seulement annuler un devis brouillon ou finalisé.” (FAIL funcional,
expectativa CANCELLED intacta). UNKNOWN-LAB llegó sólo a la guarda CRUD; su PASS
histórico se sustituye por UNRUN en la revisión estricta. Próximo run probará
Mapper.set/ValueEnum.of con control válido guardado y rollback, y un coste válido
realizado/releído antes de identificar específicamente el rechazo de coste negativo.

| Grupo completo | Estado revisado |
| --- | --- |
| CO00-NATIVE | FAIL |
| CO01-NATIVE | FAIL |
| TAX01-S-NATIVE | FAIL |
| TAX01-W-NATIVE | FAIL |
| PROD01-04 | PASS |
| VAL01-04 | FAIL |
| STATE01-04 | PASS |
| INV01-03-INSUFFICIENT | PASS |
| FX01-03-MONEY01-03 | PASS |
| PO01-09-NATIVE | UNRUN |
| PO07-09-REVISION-SELF | UNRUN |
| CASH00-06-NATIVE | UNRUN |
| BANK-BOOK-FIXTURE | PASS |
| BANK01-05-NATIVE | UNRUN |
| API01-06-SIX-ROUTES | UNRUN |
| IDEM01-02-CREATE-CONCURRENT | UNRUN |
| PERM-API-NATIVE | UNRUN |
| CASH04-06-HTTP-IMMUTABLE | UNRUN |
| SEARCH01-04-NATIVE | PASS |
| TAX02-04-IDEM-CONCURRENT | UNRUN |
| BANK-CONCURRENT-1000 | UNRUN |
| MCP01-06-STDIO | UNRUN |
| IDEM03-LOST-RESTART | UNRUN |
| IDEM04-EVENTS-RECOVERY | UNRUN |
| FIXTURE-HASH-NATIVE-EXPORT | PASS |
| AUDIT01-03-NATIVE | UNRUN |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | UNRUN |
| SUPPORTED-CONFIGURATION | UNRUN |
| STATE-UNKNOWN-ATOMIC | UNRUN |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS |
| STATE-WEB-NO-GUIDE | PASS |
| STATE-CANCEL-BEFORE-HANDOVER | FAIL |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | UNRUN |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | UNRUN |

Evidencias del commit anterior preservadas en
[runs/37440203758](evidence/axelor-core/runs/37440203758/): coverage.json usa el
comprobador congelado del run; coverage-reviewed.json aplica la revisión causal
sin atribuirle probes nuevos que no ejecutó. ZIP bloqueado sa3, un intento;
log completo estructurado conservado, sin publicar/ampliar red. Java53 pruebas,
0fallos/errores/skips, upstreamdiff0; arranque362.17s/reinicio269.94s autenticados.

## Historial CI15 (resultados exclusivos de ese commit)


Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos más manifiesto, oráculo intacto, cobertura revisión2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37435418318](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37435418318),
commit `bd1f898b25af0ec90fcbe6ab7b2b27de0b87f913`, **FAILURE**.
Los gates administrador y casos independientes ejecutados pasan. El resultado
global conserva cobertura pendiente: no se declara terminada la comparación.
Cada resultado pertenece a ese commit; no se arrastran PASS históricos.

## Gates económicos parciales — separados de los grupos completos

| Gate administrador | Estado | Tiempo | Resultado |
| --- | --- | --- | --- |
| CO00 | PASS | 10.872s | Lectura nativa después del commit y oráculo |
| TAX01-W | PASS | 5.431s | Lectura nativa después del commit y oráculo |

INVOICE_ALL completo asignó la cabecera nativa. getInvoices encontró una
factura por venta y ambas FK InvoiceLine.saleOrderLine.saleOrder;
InvoiceLine.invoice pertenece a esa factura. Cabecera/líneas/compañía coinciden
con los IDs de venta. No se sustituye el vínculo por una referencia externa.
El export completo recuperado también se revalidó independientemente con el
comprobador del mismo commit.

| Magnitud nativa | CO00 | TAX01-W |
| --- | --- | --- |
| Stock final / WAP | 3/4/5; 30/10/60 | 3/4/5; 30/10/60 |
| Valor stock / COGS | 430 / 70 | 430 / 70 |
| Ingresos / impuesto | 125 / 0 | 125 / 12.50 |
| Factura / anticipo | 125 / 50 | 137.50 / 55 |
| Banco / comisión / envío | 67 / 8 / 0 | 70.25 / 11.55 / 0.70 |
| Beneficio contable / AR restante | 47 / 0 | 42.75 / 0 |

Cuatro asientos por gate ACCOUNTED, balanceados; dos pagos confirmados por
factura, conciliación y saldo0. Son gates de administrador: sus grupos CO00 y
TAX01-W siguen **UNRUN/incompletos** hasta roles, estados, atomicidad, rechazos
e idempotencia. La atomicidad económica existente no se divide ni se desactiva.
Se confirma sólo la preparación del fixture antes de consumir Sequence aislado.

SEARCH por lector verifica la misma factura, cabecera y FK reales, misma
compañía; búsqueda y lectura de vínculo con compañía ajena devuelven403.
No se amplían grants. Permission.condition usa ? nativo, Query directo ?1.
AppInvoice efectivo/persistido mantiene PDF automático=false y
isVentilationSkipped=false. InvoiceService.validate/ventilate íntegro.
**PDF automático fuera del alcance probado**, sin PrintingTemplate/demo.

## Casos independientes del mismo CI

| Grupo | Estado | Tiempo |
| --- | --- | --- |
| PROD01-04 | PASS | 1.973s |
| SEARCH01-04-NATIVE | PASS | 0.380s |
| BANK-BOOK-FIXTURE | PASS | 0.603s |
| FX01-03-MONEY01-03 | PASS | 3.097s |
| FIXTURE-HASH-NATIVE-EXPORT | PASS | 0.105s |

PROD usa operador real, CRUD y lecturas posteriores. BANK-BOOK: cuatro
anticipos nativos, GL contabilizado, saldo255 y replay idéntico.
SEARCH: nombre/teléfono/serial, productos/paginación, factura/FK y403 ajeno.
FX completo exige y demuestra cuatro InvoicePayment, tres facturas USD y
siete GL contabilizados/conciliados: Oct1 VES40/USD1, Oct2 VES41/USD1, Oct3
dos VES0.41/USD0.01. Cotizaciones40/41/40.5 y tasa efectiva redondeada se
comprueban con fechas/importes/IDs y lecturas posteriores al commit; saldos0.
Rechazos sin efectos y autorización gerente ejecutados. Conversión parcial
se conserva aparte; el agregador rechaza cálculos/tasas sin pagos nativos.

## Matriz de 34 grupos — CI finalizado

**PASS5** / **FAIL0** / **BLOCKED0** / **UNRUN29**.
Los UNRUN incluyen los dos gates parciales; el resto sigue sin aceptación completa.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | --- | --- | --- |
| CO00-NATIVE | 1 | UNRUN | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | UNRUN | No |
| PROD01-04 | 1 | PASS | Sí |
| VAL01-04 | 1 | UNRUN | No |
| STATE01-04 | 1 | UNRUN | No |
| INV01-03-INSUFFICIENT | 1 | UNRUN | No |
| FX01-03-MONEY01-03 | 1 | PASS | Sí |
| PO01-09-NATIVE | 1 | UNRUN | No |
| PO07-09-REVISION-SELF | 1 | UNRUN | No |
| CASH00-06-NATIVE | 1 | UNRUN | No |
| BANK-BOOK-FIXTURE | 1 | PASS | Sí |
| BANK01-05-NATIVE | 1 | UNRUN | No |
| API01-06-SIX-ROUTES | 1 | UNRUN | No |
| IDEM01-02-CREATE-CONCURRENT | 1 | UNRUN | No |
| PERM-API-NATIVE | 1 | UNRUN | No |
| CASH04-06-HTTP-IMMUTABLE | 1 | UNRUN | No |
| SEARCH01-04-NATIVE | 1 | PASS | Sí |
| TAX02-04-IDEM-CONCURRENT | 1 | UNRUN | No |
| BANK-CONCURRENT-1000 | 1 | UNRUN | No |
| MCP01-06-STDIO | 2 | UNRUN | No |
| IDEM03-LOST-RESTART | 1 | UNRUN | No |
| IDEM04-EVENTS-RECOVERY | 2 | UNRUN | No |
| FIXTURE-HASH-NATIVE-EXPORT | 1 | PASS | Sí |
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
| --- | --- |
| 1 | UNRUN |
| 2 | PASS |
| 3 | UNRUN |
| 4 | UNRUN |
| 5 | UNRUN |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | UNRUN |
| 12 | UNRUN |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio2 proviene de suites/WAR/pins/diffs upstream del mismo commit; nunca
PASS preasignado. Criterio12 requiere benchmark/restauración adicional: SEARCH
funcional PASS no lo completa. Criterio13 BLOCKED por actualización diferida
a copia aislada con objetivo aprobado; seis PATCH UNRUN. Recovery y auditoría
integral tampoco se aprueban por smoke.

## Validaciones y métricas

- 40 tests Java reales: 2baseline+7política+8dirección+5filtros+2flags+
  16upstream, cero fallos/errores/skips. Python ejecutó 30 regresiones.
- Preflight HTTP AddressBaseRepository completo PASS: save/render/compute,
  plantilla con cinco hijos/metadatos y campos requeridos, lectura/replay.
- Readiness inicial326.02s; reinicio misma DB257.89s;
  job15min44s. Login/REST autenticados, AOP8.2.3/AOS9.1.8,
  módulo0.1.0, 33módulos.
- CPU4/afinidad4; disco libre87087382528bytes.
  HTTP por actor: `{"administrator": 32, "product_operator": 30, "search_reader": 16, "fx_operator": 11, "fx_manager": 4}`.
- p50/p95/p99, 1000muestras y query/DB timing: UNRUN.
- Ambos upstreams fijados diff0; pins SHA256 `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
  WAR SHA256 `96210618a6ec7646dc76bf8ab9e24c7967635a589e383038784e1eb06d2b6be2`.

## Evidencia y continuidad

[coverage.json](evidence/axelor-core/runs/37435418318/coverage.json),
[CO00](evidence/axelor-core/runs/37435418318/CO00-native-export.json),
[TAX01-W](evidence/axelor-core/runs/37435418318/TAX01-W-native-export.json),
[SEARCH/lector](evidence/axelor-core/runs/37435418318/SEARCH01-04-NATIVE.json),
[cuatro pagos FX](evidence/axelor-core/runs/37435418318/FX01-03-MONEY01-03.json),
[atestación build](evidence/axelor-core/runs/37435418318/build-evidence.json),
[métricas](evidence/axelor-core/runs/37435418318/runtime-metrics.json),
[procedencia/hashes](evidence/axelor-core/runs/37435418318/evidence-source.json).
Fuente secundaria: JSON completos del log, validados con código del mismo SHA.
ZIP11399482551: un intento Forbidden en productionresultssa4.blob.core.windows.net;
sin ampliar ni publicar red. Log recuperable: `/workspace/ccm-axelor-runtime/ci-evidence/37435418318.log`.

CI es fuente de aceptación. Docker/PostgreSQL local no equivalen a ERP fiable;
el diagnóstico JPA anterior quedó en RequestScoped/saveUNRUN. El preflight
HTTP real ya pasó. Sin permisos del sistema ni credenciales persistentes nuevas.
Sin PR/merge/despliegue ni cambios main/Frappe/pins/upstream. Arranque guardado
sólo en borrador; publicación de red pendiente no se ejecuta.
