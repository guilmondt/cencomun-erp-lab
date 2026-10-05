# Task 100 — Cencomun Core Test

Do not start until the relevant baseline task passes.

Implement docs/CORE_TEST_SPEC.md for exactly one platform per branch/task. Create an ExecPlan before coding.

Report requirements passed/failed, extension points used, upstream files changed (target zero), migrations/data changes, tests/results, files/LOC (informational), performance observations, workarounds, and upgrade-risk observations.

## ExecPlan — comparación acotada con perfil sintético compartido

Revisado: **2026-10-05 (America/Caracas)**. Estado: **aprobado por el usuario para el laboratorio;
implementación y ejecución Frappe autorizadas en lab/frappe-baseline**. El cuestionario se detiene, incluida D04-A.
Las respuestas del usuario se conservan en ADR-003–007 y en la tabla siguiente;
no se vuelven a preguntar. ADR-008 conserva el cambio de método. ADR-010 registra la autorización explícita
de LAB-ONLY-v1 y su ejecución aislada; no autoriza políticas de producción.
Corrección de esta revisión: caso fiscal común con impuesto incluido distinto
de cero y cierre del informe con limitaciones técnicas documentadas (ADR-009).

### Objetivo, alcance y condiciones

Comparar Frappe/ERPNext y Axelor ejecutando el mismo manifiesto `ccm-core-v1`,
el mismo perfil `LAB-ONLY-v1` y el mismo oráculo de resultados. Se reutilizan
`docs/CORE_TEST_SPEC.md`, los 14 `docs/ACCEPTANCE_CRITERIA.md`,
`docs/COMPARISON_PROTOCOL.md`, el charter y las seis rutas del contrato existente.
Se mantienen sus siete bloques: producto, Cashea, caja, compras, banco,
API/eventos/MCP y búsqueda. Inventario y contabilidad se prueban mediante
mecanismos nativos vinculados a esos bloques, sin crear motores propios.

Este turno modifica únicamente documentación en `lab/frappe-baseline`.
No cambia Axelor, main, contratos ejecutables, aplicaciones, datos, versiones ni
pins. Después de revisar el plan, la ejecución requerirá una instrucción explícita
y se hará en una plataforma por rama/tarea. No hay integración real con Cashea,
impresión fiscal, bundles a precio cero ni automatización del tarifario MRW.

### 1. Reglas confirmadas: se conservan sin sustituirlas

| Tema | Respuesta confirmada y efecto en las pruebas |
| --- | --- |
| Garantía | Cantidad entera no negativa + DAY/MONTH/YEAR; 0 significa sin garantía. Conservar 30 DAY, 6 MONTH, 1 YEAR y los pares con cero; no convertir unidades silenciosamente |
| Producto/publicación | Financiación en tienda y visibilidad son independientes; Pausada no deshabilita por sí sola Cashea. Conservar precio al deshabilitar Cashea y ambos códigos SKU/proveedor cuando difieran |
| Precio/cantidad | Precio final USD con impuestos incluidos; positivo en venta ordinaria; precios/totales hasta dos decimales, tasas hasta seis; cantidades solo enteras |
| Comisión | Tienda: 4% del total final de productos + 4% del financiado. Web: 6% del total final + 4% del financiado. No aplicar ambos porcentajes solo al financiado |
| Costo y gastos | Costo nativo del ERP, sin costos negativos; comisión y envío son gastos separados. Se retira la propuesta de elegir/congelar costo según creación, aprobación o despacho |
| Envío web | Cencomun absorbe el cargo, no lo cobra al cliente y Cashea lo descuenta de la liquidación. Registrar un gasto y su pago por retención, sin duplicarlos. Usar importes conocidos del tarifario; no extrapolarlo |
| Canales | Cashea web entrega orden + guía; Cencomun despacha. Cashea en tienda es venta y entrega directa, sin guía ni transporte |
| Bruto/neto/resultado | Bruto = total final de productos. Neto = bruto - comisión - envío. Resultado = neto - costo ERP; mostrar importe y porcentaje sobre ventas, sin mezclar gasto con costo de inventario |
| Dinero y tasa | Redondeo decimal half-up de líneas y suma de sus resultados; tasa de la fecha del pago. Si falta, entrada manual solo autorizada; no usar automáticamente una tasa antigua |
| Excepción aplazada | Accesorios de combos a precio cero autorizados por gerente, su descarga/costo y comentario fiscal: conservar la respuesta, estudiar después y excluir de esta implementación |

Los límites de compra **ya fijados en CORE_TEST_SPEC** se conservan: <=200 USD
comprador; >200 y <=1000 gerente; >1000 director. No se solicita redefinirlos.
La plantilla aporta los catálogos Nuevo/Usado/Reacondicionado y Activa/Pausada;
no determina por sí sola políticas de stock, impuestos ni liquidación.

### 2. Supuestos propuestos exclusivamente para el laboratorio

Cada uno se identifica como `LAB`, se versiona con el manifiesto y se aplica
igual a ambos ERP. **No son políticas reales de Cencomun** ni respuestas dadas
por el usuario. Revisar este plan no los convierte en decisiones de producción.

| ID | Regla sintética compartida y motivo |
| --- | --- |
| L01 — aislamiento | Empresa CCM-LAB-001, almacén WH-LAB-001, monedas USD/VES, unidad entera. Fecha base 2026-10-01; sin clientes/bancos reales. CO00/CO01 mantienen impuesto sintético 0%; TAX01-S/TAX01-W usan 10% incluido en el precio. Son datos LAB, sin afirmar exención ni tasa fiscal real |
| L02 — stock/costo | Existencia inicial P001/P002/P003 = 5/5/5; entrada nativa a costos 30/10/60 USD. Sin reservas ni nuevas entradas durante cada escenario. Stock negativo deshabilitado; qty >0. Valorar con el mecanismo nativo, que en este fixture de costo uniforme produce los mismos importes |
| L03 — estados | Simulador autenticado de Cashea aporta aceptación/cancelación/liquidación; REVIEWED es validación técnica y APPROVED es aceptación simulada, sin aprobación manual del comerciante. Recepción web prueba una orden ya originada, sin simular el catálogo público ni cancelar automáticamente por publicación actualmente pausada. Caminos y efectos definidos abajo |
| L04 — cobros | Pago directo = total final - financiado; transferencia Cashea = financiado - comisión - envío web. CO00/CO01: total 125, financiado 75, pago directo 50. TAX01-S/TAX01-W: total 137.50, financiado 82.50, pago directo 55.00. Este reparto es sintético; no se presume que describa contratos reales |
| L05 — caja | Esperado = apertura + movimientos efectivamente recibidos - reembolsos pagados + ajustes con signo. Comparar por canal/moneda; diferencia = observado - esperado. Cashea pendiente se informa aparte, sin contarlo como efectivo; POS representa cobro capturado, no depósito bancario |
| L06 — cierre | Operador prepara; gerente confirma. Con diferencia, exigir nota antes de confirmar. Cierre confirmado inmutable en este perfil; edición/corrección directa rechazada y auditada. El proceso real de corrección se aplaza |
| L07 — compras | Base = total final con impuestos/cargos - descuentos; sin escalones previos. Rol mínimo por umbral; gerente puede aprobar nivel comprador y director cualquier nivel. No autoaprobación; monto <=0 inválido; cambio de monto invalida aprobación. Conversión previa a pago: tasa sintética de fecha de solicitud, solo para este caso |
| L08 — banco | Clave de transacción = SHA-256 de cuenta/fecha/referencia/moneda/importe con signo, normalizados; descripción no es parte de ella. Clave de archivo = empresa/cuenta/SHA-256 de bytes. Exacto: esos cinco campos iguales; probable: importe/moneda/cuenta iguales y fecha dentro de ±2 días. Solo exacto único puede conciliar automáticamente; probable/ambiguo requieren decisión del gerente |
| L09 — tasas | Fuente local ficticia: 40.000000 VES/USD el 2026-10-01 y 41.000000 el 2026-10-02. Cada pago conserva fecha y tasa. Gerente autoriza tasa manual dejando motivo; dos pagos en fechas distintas usan sus respectivas tasas, no una media inventada |
| L10 — roles | Matriz mínima de prueba abajo; restricciones por empresa. Una credencial MCP solo lee/crea borradores/pedidos NEW, sin aprobar, entregar, liquidar, confirmar caja ni conciliar |
| L11 — integración | Claves estables, persistencia de resultado de reintento y deduplicación; eventos con entrega al menos una vez y consumidor idempotente. El contrato sintético de errores/paginación queda definido abajo, sin añadir rutas de negocio |
| L12 — impuesto incluido | Impuesto de venta sintético TAX-LAB-10 = 10%, incluido en precios finales de TAX01; base de cada línea = total de línea / 1.10, impuesto = total - base, con half-up por línea. Ingreso sin impuesto y pasivo tributario separados por el ERP; comisión calculada sobre total con impuesto. Comisiones/envío no llevan impuesto adicional en este fixture; no hay retención fiscal ni pago del impuesto simulado |

### 3. Mapeo técnico Cashea tienda/web y ERP nativo

`channel = STORE | WEB`; no inferirlo del estado de publicación del producto.
El estado Cashea es propio de la extensión Cencomun y conserva referencias a
los documentos nativos: no se confunde con el estado de una factura ni se
escriben directamente estados nativos o tablas del ERP.

| Etapa normalizada LAB | STORE: venta/entrega directa | WEB: orden con guía/despacho | Efectos comunes esperados |
| --- | --- | --- | --- |
| NEW -> REVIEWED | Captura y validación de datos | Captura de orden con guía ficticia GUIDE-LAB-001 y validación | Sin salida de stock, cobro ni evento de éxito |
| REVIEWED -> APPROVED | Aceptación simulada Cashea | Aceptación simulada Cashea | Pedido nativo confirmado por servicios soportados; un evento cashea.approved, sin salida física |
| Preparación | No existe paso de transporte | APPROVED -> PREPARING | Puede preparar el documento nativo; stock físico sin cambios |
| Entrega | APPROVED -> FULFILLED: entrega al cliente | PREPARING -> SHIPPED: entrega al transportista; requiere guía | Una salida nativa y una factura final por pedido; qty -2/-1; valor de stock -70 USD |
| Liquidación | FULFILLED -> SETTLED | SHIPPED -> SETTLED | Pago directo según L04 + transferencia Cashea neta; saldo pendiente 0; gastos contabilizados una vez |
| Excepciones sintéticas | REJECTED desde NEW/REVIEWED; CANCELLED antes de entrega | REJECTED desde NEW/REVIEWED; CANCELLED desde NEW/REVIEWED/APPROVED/PREPARING | Sin salida física ni factura contabilizada/cobros; cancelar documentos auxiliares por servicios nativos. No simular una devolución después de entregar |

NEW -> SETTLED, estados desconocidos, saltar aceptación, cancelar después de
FULFILLED/SHIPPED y despachar web sin guía se rechazan sin efecto parcial.
`FULFILLED` expresa entrega en tienda, **no envío**; `SHIPPED` se conserva para
web. El tramo técnico de validación/aceptación puede procesarse seguido al
recibir el mensaje del simulador; no exige tareas manuales al negocio.
Un reintento con la misma clave devuelve el resultado ya persistido; una segunda
petición distinta para la misma entrega devuelve conflicto, sin repetir efectos.

| Objeto/efecto | Frappe/ERPNext v16.36.1 | Axelor Open Suite v9.1.8 |
| --- | --- | --- |
| Extensión producto/cliente | Item con campos Cencomun; Customer | Product ampliado por módulo Cencomun; Partner cliente |
| Pedido y estado Cashea | DocType Cencomun con hijos/lazos a Sales Order; métodos de app, validación y permisos en servidor | Entidad Cencomun con líneas/lazos a SaleOrder; servicios transaccionales y seguridad del módulo |
| Pedido nativo aprobado | Sales Order sometido mediante su ciclo soportado | SaleOrder confirmado mediante su servicio; no cambiar statusSelect directamente |
| Salida física STORE/WEB | Un Delivery Note sometido; marca de entrega directa o guía según canal | Un StockMove de salida realizado; entrega directa o trackingNumber según canal |
| Factura/cobros/gastos | Sales Invoice con update_stock desactivado porque Delivery Note ya descargó; Payment Entry y cuentas de gastos/retenciones mediante APIs nativas | Invoice y pagos/movimientos contables soportados, vinculados al StockMove; evitar generar otro movimiento de stock al facturar |
| Stock nativo | Existencia y valoración del almacén; no el stock del portal Cashea | StockLocationLine.currentQty y valoración nativa; no usar futureQty como existencia física |
| Importación bancaria | Bank Transaction y conciliación soportada | BankStatementLine (módulo bank-payment) y conciliación soportada |

Los DocTypes locales de ERPNext y dominios XML públicos de Axelor en su tag
v9.1.8 se consultaron para comprobar estos nombres/campos. Esto resuelve el diseño
objetivo; no prueba ejecución ni módulos habilitados en el entorno Axelor.
La ejecución verificará servicios/configuración y registrará cualquier carencia
como hallazgo, manteniendo el mismo resultado requerido y sin suplir stock,
contabilidad o permisos con SQL o un motor externo.
Fuentes de mapeo: ERPNext local, commit
fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba; Axelor
[SaleOrder](https://github.com/axelor/axelor-open-suite/blob/v9.1.8/axelor-sale/src/main/resources/domains/SaleOrder.xml),
[StockMove](https://github.com/axelor/axelor-open-suite/blob/v9.1.8/axelor-stock/src/main/resources/domains/StockMove.xml),
[StockLocationLine](https://github.com/axelor/axelor-open-suite/blob/v9.1.8/axelor-stock/src/main/resources/domains/StockLocationLine.xml),
[Invoice](https://github.com/axelor/axelor-open-suite/blob/v9.1.8/axelor-account/src/main/resources/domains/Invoice.xml)
y [BankStatementLine](https://github.com/axelor/axelor-open-suite/blob/v9.1.8/axelor-bank-payment/src/main/resources/domains/BankStatementLine.xml).

### 4. Datos y escenarios con resultados esperados

Manifiesto propuesto `ccm-core-v1`: IDs funcionales comunes, decimales como texto,
reloj explícito y hashes por archivo. Cada escenario económico parte de su
snapshot inicial propio; CO00/CO01 no se ejecutan acumulando el stock de otro.
C001/C002 son Cliente ficticio Alfa/Beta, correos alfa/beta@example.invalid y
+12025550101/+12025550102. Proveedor SUP-LAB y cuenta BANK-USD-001 son ficticios.

| Producto | Publicación / Cashea | Precio final / costo ERP USD | Referencia / garantía / condición |
| --- | --- | --- | --- |
| P001, Equipo ficticio Alfa | true / true | 50.00 / 30.00 | SUP-ALFA-01; 12 MONTH; NEW |
| P002, Accesorio ficticio Beta | false / true | 25.00 / 10.00 | SUP-BETA-02; 6 MONTH; REFURBISHED |
| P003, Equipo ficticio Gamma | true / false | 80.00 / 60.00 | SUP-GAMMA-03; 0 MONTH; USED |

CO00 y CO01 tienen 2 × P001 + 1 × P002, total 125.00, costo ERP 70.00 y
financiado 75.00. Las cifras siguientes son **esperadas, no tests ejecutados**.

| Caso | Comisión / envío USD | Neto agregado / resultado USD | Cobros sintéticos L04 / resultado físico |
| --- | --- | --- | --- |
| CO00 STORE | 5.00 + 3.00 = 8.00 / 0.00 | 117.00 / 47.00; margen sobre ventas 37.60% | Cliente 50.00 + Cashea 67.00; FULFILLED -> SETTLED, sin guía |
| CO01 WEB | 7.50 + 3.00 = 10.50 / 0.70; paquete 0.800 kg | 113.80 / 43.80; margen sobre ventas 35.04% | Cliente 50.00 + Cashea 63.80; SHIPPED -> SETTLED, GUIDE-LAB-001 |

En ambos: stock inicial 5/5/5 y valor 500.00; después de entrega stock 3/4/5
y valor 430.00. Salida de inventario valorada en 70.00 una vez; comisión/envío
no alteran el costo de producto. Tras factura final, saldo cliente 125.00;
tras pago directo 75.00; tras liquidación Cashea 0.00. Por liquidación se aplican
75.00 a la deuda: transferencia + comisión + envío = 75.00. El neto agregado
117.00/113.80 incluye el pago del cliente: no se confunde con la transferencia
Cashea 67.00/63.80. Asientos nativos equilibrados y vínculos auditables.

#### Caso fiscal común TAX01: impuesto incluido del 10%

Se ejecutan las dos variantes **TAX01-S (STORE)** y **TAX01-W (WEB)** en cada
ERP con entradas y resultados idénticos. Cada una parte de un snapshot propio.
Solo en este escenario, P001 tiene precio final 55.00 USD y P002 27.50 USD;
sus costos nativos permanecen 30.00 y 10.00. Se conservan cantidades 2 y 1,
stock inicial 5/5/5, cliente C001, fecha 2026-10-01 y todos los demás campos.
No se sobrescriben los precios de los fixtures CO00/CO01.

| Línea común | Qty | Precio unitario final USD | Total con impuesto USD | Ingreso/base sin impuesto USD | Impuesto incluido USD |
| --- | --- | --- | --- | --- | --- |
| P001 | 2 | 55.00 | 110.00 | 100.00 | 10.00 |
| P002 | 1 | 27.50 | 27.50 | 25.00 | 2.50 |
| Total | 3 | — | 137.50 | 125.00 | 12.50 |

No sumar otro 10% sobre 137.50: el impuesto ya está incluido. Financiado
82.50 USD; pago directo 55.00; costo de productos 70.00. En WEB, guía ficticia
GUIDE-LAB-TAX-001, paquete 0.800 kg y envío retenido 0.70 USD. STORE no exige guía
ni tiene envío. Los caminos/permisos son los mismos que CO00/CO01 según canal.

| Resultado esperado, idéntico por ERP | TAX01-S STORE | TAX01-W WEB |
| --- | --- | --- |
| Total final / ingreso sin impuesto / pasivo tributario USD | 137.50 / 125.00 / 12.50 | 137.50 / 125.00 / 12.50 |
| Comisión sobre total con impuesto | 0.04 × 137.50 = 5.50 | 0.06 × 137.50 = 8.25 |
| Comisión sobre financiado | 0.04 × 82.50 = 3.30 | 0.04 × 82.50 = 3.30 |
| Gasto total de comisión / gasto de envío USD | 8.80 / 0.00 | 11.55 / 0.70 |
| Transferencia Cashea neta USD | 73.70 | 70.25 |
| Neto agregado cobrado, incluido pago directo USD | 128.70 | 125.25 |
| Indicador Cashea previamente acordado: neto agregado - costo USD | 58.70 | 55.25 |
| Resultado contable LAB: ingreso sin impuesto - costo - comisión - envío USD | 46.20 | 42.75 |
| Stock final P001/P002/P003 / valor total USD | 3/4/5 / 430.00 | 3/4/5 / 430.00 |
| Saldo cliente: factura / tras pago directo / tras liquidación USD | 137.50 / 82.50 / 0.00 | 137.50 / 82.50 / 0.00 |

El indicador Cashea conserva la fórmula previamente confirmada, pero con
impuesto incluido **no se presenta como utilidad contable**: contiene los 12.50
del impuesto cobrado. Resultado contable = ingreso sin impuesto 125.00 - costo
70.00 - gastos; también equivale al indicador Cashea - impuesto 12.50.
El impuesto es pasivo, no ingreso ni comisión; no se descuenta de la transferencia
Cashea en este fixture ni se simula su remisión al fisco.

Asientos funcionales esperados por escenario, **todos en contabilidad nativa**:

| Operación | Debe USD | Haber USD |
| --- | --- | --- |
| Factura final, ambos canales | Cuenta por cobrar cliente 137.50 | Ingreso por ventas 125.00 + impuesto por pagar 12.50 |
| Salida de productos, ambos canales | Costo de ventas 70.00 | Inventario 70.00 |
| Pago directo del cliente, ambos canales | Efectivo USD 55.00 | Cuenta por cobrar cliente 55.00 |
| Liquidación TAX01-S | Banco USD 73.70 + gasto de comisión 8.80 | Cuenta por cobrar cliente 82.50 |
| Liquidación TAX01-W | Banco USD 70.25 + gasto de comisión 11.55 + gasto de envío 0.70 | Cuenta por cobrar cliente 82.50 |

Normalizar por categorías de cuenta, documento/escenario, moneda y suma de
Debe/Haber, no por los códigos de cuenta o el número de asientos internos de
cada ERP. Ambos deben dar estos saldos/efectos exactos, asientos equilibrados,
pasivo de impuesto 12.50 y trazabilidad a factura, salida y liquidación. La carga
inicial de inventario pertenece al snapshot y se excluye de los movimientos de
venta comparados. Usar valoración/contabilidad de inventario nativa configurada;
si un efecto no puede verificarse, registrar FAIL o BLOCKED según la causa,
sin sustituirlo con un cálculo externo presentado como contabilización.

Mapeo fiscal propuesto: ERPNext usa su impuesto de venta incluido en precio
(`included_in_print_rate`) y Sales Invoice sin nueva salida de stock. Axelor usa
precio con impuestos (`inAti`), impuesto sintético y separación nativa
`exTaxTotal`/`taxTotal`/`inTaxTotal` en Invoice; mantener un solo StockMove.
Crear/configurar y contabilizar por mecanismos soportados, sin SQL de negocio.

Pruebas comunes TAX01–04: desglose de líneas/impuesto; comisiones sobre 137.50
y 82.50 (nunca sobre 125.00 para el primer componente); asientos/saldos separados;
y reintento/concurrencia/reinicio sin segunda factura, salida, comisión ni pasivo
tributario. Aplicar las pruebas de denegación y auditoría a ambas variantes.

| Grupo / escenarios | Entradas y resultado idéntico requerido |
| --- | --- |
| PROD01–04 | Persistir/leer/exportar siete campos; pares 30 DAY, 6 MONTH, 1 YEAR y 0 DAY/MONTH/YEAR intactos. P002 pausado puede financiar en STORE; P003 no habilitado se rechaza como venta Cashea en LAB. Deshabilitar P001 conserva 50.00 |
| VAL01–04 | Precio ordinario 0 o negativo, costo negativo, qty 0/0.5/negativa y precio 0.005: rechazo. En LAB también rechazar financiado <0 o >total. No crear efectos de negocio tras el rechazo |
| MONEY01–03 | Líneas 100.00/25.00 y fórmulas CO00/CO01 exactas. Dos líneas 0.01 USD × tasa 40.500000 dan 0.41 + 0.41 = 0.82 VES, no 0.81. Componentes de comisión LAB: half-up a dos decimales y suma, conservando las bases |
| TAX01–04, STORE/WEB | Impuesto incluido 10%: total 137.50 = ingreso 125.00 + impuesto 12.50; comisión 8.80/11.55; gastos separados; resultado contable 46.20/42.75; stock/saldo cliente y asientos nativos según tablas. Repetir operación no duplica impuesto ni otros efectos |
| FX01–03 | Pagos de 1 USD los días 01/02 producen 40.00/41.00 VES con sus tasas; no convertir ambos al mismo día. Tasa ausente bloquea pago; operador no puede introducirla; gerente con motivo sí, conservando actor/fecha/valor |
| STATE01–04 | Ambos caminos válidos; rechazos/cancelaciones sintéticos antes de entregar mantienen stock 5/5/5. Saltos inválidos y cancelación posterior no cambian stock, saldo, estado ni emiten éxito |
| INV01–03 | CO00/CO01 descargan exactamente una vez. Intentar entregar 6 unidades P001 con solo 5: rechazo, cero salida/factura contabilizada y estado previo intacto. Reintentos/concurrencia de misma entrega no generan segundo documento ni gasto |
| CASH00–03 | CS000 coincide en todos los canales, diferencias 0. CS001: USD esperado 100/observado 98 -> -2.00; VES 4000/4010 -> +10.00; POS 50/50 y transferencia 30/30 -> 0. Cashea pendiente 125 y recibido 0 se informan aparte, sin sumarlos a efectivo |
| CASH04–06 | Gerente confirma CS000; CS001 solo con nota de diferencia. Operador no confirma. Tras confirmar, edición UI/API rechazada; originales/actor/instante intactos y un evento cash.closing.confirmed. Reintentar no duplica cierre/evento lógico |
| PO01–06 | 199.99 y 200.00 -> comprador; 200.01, 999.99 y 1000.00 -> gerente; 1000.01 -> director. Actor inferior y autoaprobación rechazados. Un evento purchase.approved por aprobación válida |
| PO07–09 | L07: 180 + impuestos sintéticos 15 + envío 10 - descuento 5 = 200 -> comprador. 8000.00/8000.40 VES a 40 en solicitud -> 200.00/200.01 USD, comprador/gerente. Cambiar 200 aprobado a 200.01 vuelve a pendiente; 0/negativo inválidos |
| BANK01–05 | T001 exacto, T002 probable, T003 ambiguo, T004 duplicado, T005 sin pareja según tabla siguiente. Importación repetida/concurrente no añade transacciones ni conciliaciones; decisión manual auditada |
| API/MCP01–06 | Seis rutas, equivalencia de lectura/creación por API/MCP; 401 anónimo, 403 rol/empresa indebida, 422 entrada inválida, 409 conflicto de estado/idempotencia. Sin cambios parciales ante error; MCP no puede invocar aprobación/entrega por otra vía |
| AUDIT01–03 | Cambios de estado, cierre, aprobación, tasa manual y conciliación guardan actor/instante/objeto/antes-después/motivo/correlación. Roles de negocio no editan ni borran auditoría; rechazo de permisos deja registro sin evento de éxito |
| IDEM01–04 | Repetir clave y payload conserva IDs/importes/stock; misma clave con payload distinto -> 409. Dos llamadas simultáneas, reinicio tras commit antes de responder y reentrega de evento producen un solo efecto y permiten recuperar el resultado |
| SEARCH01–04 | P001/código/nombre, SUP-BETA-02, teléfono/nombre C001 e INV-CCM-001 devuelven conjunto exacto sin duplicación. Inexistente -> []. Paginación completa respetando empresa/rol; serial SER-P001-001 donde soporte nativo, carencia documentada |

CS000/CS001 utilizan movimientos nativos ficticios verificables: USD apertura
20 + recibido 84 - reembolso 5 + ajuste 1 = 100; VES apertura 1000 + recibido
3000 = 4000. El reembolso/ajuste son movimientos de caja del fixture, sin nuevo
flujo de devoluciones de productos. No agregar USD y VES ni derivar automáticamente
asientos de faltante/excedente: aquí se verifica cierre y auditoría.

Banco: registros internos BK001 (01, EXACT-001, +100 USD), BK002 (02,
PROB-BOOK-001, +75), BK003/BK004 (03, AMB-BOOK-A/B, +40), todos en BANK-USD-001.
Cargar sus movimientos por servicios nativos. Los días son de octubre de 2026.

| CSV account/date/reference/currency/amount/description | Clasificación esperada LAB y acción |
| --- | --- |
| T001: cuenta anterior / 01 / EXACT-001 / USD / +100.00 / Cobro ficticio exacto | EXACT: BK001 único; una conciliación |
| T002: misma cuenta / 03 / PROB-BANK-001 / USD / +75.00 / Cobro ficticio probable | PROBABLE: solo BK002; no conciliar sin gerente |
| T003: misma cuenta / 03 / AMB-BANK-001 / USD / +40.00 / Cobro ficticio ambiguo | AMBIGUOUS: BK003 y BK004; no elegir arbitrariamente; gerente puede seleccionar BK003 dejando BK004 pendiente |
| T004: repetición idéntica T001 | DUPLICATE: no insertar ni conciliar otra vez |
| T005: misma cuenta / 04 / NO-MATCH-001 / USD / +999.00 / Sin pareja | UNMATCHED: sin candidato |

CSV real futuro usa fechas ISO YYYY-MM-DD. Primera importación: 5 filas, 4
transacciones únicas, 1 duplicado y 1 conciliación automática. Tras aprobar T002
y seleccionar BK003 para T003: 3 conciliaciones; T005 y BK004 pendientes.
Reimportar mismo archivo devuelve resultado previo; otro archivo con esas mismas
transacciones añade 0 transacciones y 0 conciliaciones. Signo positivo = abono,
negativo = cargo; escenario adicional -10 sin pareja preserva el signo y añade
una transacción independiente. Comisiones bancarias con diferencia de importe
no se compensan automáticamente en LAB; quedan sin pareja para decisión futura.

### 5. Permisos, contrato e idempotencia del perfil LAB

| Actor ficticio | Permitido | Denegado expresamente |
| --- | --- | --- |
| U_READER | Lecturas de empresa autorizada | Toda escritura y auditoría privada |
| U_OPERATOR | Editar producto, crear pedidos/borradores, entregar/despachar, preparar caja e importar CSV | Aceptar/liquidar por Cashea, aprobar compras, confirmar caja, tasa manual, decidir conciliación |
| U_BUYER / U_MANAGER / U_DIRECTOR | Compras según umbral L07; gerente además cierre/tasa manual/conciliación | Autoaprobación y acciones fuera de su matriz; no heredar permisos financieros por ser director |
| U_CASHEA_SIM | Mensajes autenticados de aceptación/cancelación/liquidación sintética | Editar productos o ejecutar salida física por su cuenta |
| U_MCP | Lecturas, borrador de compra y pedido NEW vía seis rutas | Aprobaciones, stock de salida, cierre, tasa y conciliación; acceso directo DB |
| U_ANON / actor de otra empresa | Nada sobre objetos de CCM-LAB-001 | 401/403 respectivamente, sin fuga de datos ni efectos |

Los aprobadores son identidades distintas del creador. Probar matriz mediante
API y métodos nativos, no únicamente ocultando botones. Concurrencia/atomicidad,
trazabilidad y deduplicación se implementarán dentro de extensiones soportadas;
contabilización y movimientos físicos siguen perteneciendo al ERP.
Para el caso negativo de autoaprobación, una identidad ficticia reúne roles
de creación y aprobación; tener ambos no elimina la prohibición LAB de aprobar
su propio documento. No se supone que esos roles existan así en producción.

Contrato LAB para las seis rutas actuales: IDs funcionales + company_id; moneda
ISO; dinero textual con dos decimales y tasas hasta seis; fechas ISO con offset.
GET search usa q, page, page_size (2 en el caso paginado), orden por ID funcional,
items y total. GET inventory devuelve on_hand, reserved=0 y available=on_hand
para este perfil sin reservas, además de unidad/almacén. GET balance devuelve
saldo de facturas contabilizadas menos pagos/aplicaciones, por moneda, incluyendo
saldo C002=0.00. GET cash devuelve estado y cifras por moneda/canal, sin convertir.
POST purchase crea DRAFT y POST Cashea crea NEW, sin aprobación implícita.
Primera creación 201; reintento válido 200 con replay=true y mismo ID.

Requerir Idempotency-Key en escrituras del adaptador. Alcance empresa/operación;
hash del payload normalizado persistido, exclusión/clave única para concurrencia
y recuperación tras reinicio. Operaciones nativas de transición usan la misma
protección sin añadir nuevas rutas comerciales al contrato actual. Error común:
code, message, correlation_id, sin detalles privados del framework.
Autenticación/autorización se verifican también antes de devolver un replay;
conocer una clave no permite acceder al resultado de otra empresa o rol indebido.
Eventos cashea.approved, cash.closing.confirmed y purchase.approved incluyen
schema_version, event_id estable, object_id, company_id, actor, occurred_at y
correlation_id; registro durable vinculado al commit y deduplicación del consumidor.
Identidad lógica de evento: tipo/objeto/versión de decisión. Una reaprobación
válida tras cambiar el monto es una decisión nueva; reintentar la misma no lo es.
Ante caída tras commit, el evento debe recuperarse; transporte repetido permitido,
efecto de negocio repetido no. No se afirma entrega exactamente una vez.

### 6. Decisiones de producción aplazadas y preguntas necesarias

| Tema anterior | Resuelto para comparar | Lo que permanece aplazado en producción |
| --- | --- | --- |
| D03/D08 tasas | L09 y matriz LAB | Fuente real general, responsables y pagos en distintas fechas según contratos reales |
| D04 estados | L03 y mapeo STORE/WEB | Procedimiento real de cancelación/rechazo, devoluciones y comunicaciones con Cashea |
| D05 caja/cobros | L04–06 | Anticipos/liquidaciones reales, depósitos POS, política de diferencias y correcciones de cierre |
| D06 compras | L07, umbrales conservados | Autoaprobación/jerarquía real, base de cargos y tasa antes de pago en producción |
| D07 banco | L08, CSV ficticio | IDs reales de bancos, tolerancias reales, cargos y autorización de conciliación |
| D08 permisos | L10 y pruebas negativas | Roles reales, empresas/sucursales y separación efectiva de funciones |
| Exportación/localización | Formato registrado, sin carga | Reparar plantilla antes de carga autorizada, variantes, MRW automático, fiscal y combos cero |
| T01/T02 | Contrato LAB y medición sintética | Consumidores/contratos reales, volumen/SLA de operación; no convertir el benchmark en afirmación de capacidad productiva |

**No queda una decisión de negocio imprescindible para preparar ni ejecutar
este perfil una vez revisado y autorizado. No se solicitan respuestas nuevas.**
Los supuestos LAB fueron aprobados explícitamente para esta evaluación.
Las decisiones de producción siguen aplazadas; no se adoptan por silencio. Un impedimento técnico se registra y resuelve como tal; solo
preguntar si no existe una alternativa sintética que preserve la comparación.

### 7. Secuencia futura y criterio para terminar la comparación

1. Revisar este plan; después, recibir instrucción explícita de implementación.
   Congelar LAB-ONLY-v1, manifiesto, casos/errores, hashes y mapping. Autorizado:
   fixtures materializados en fixtures/ccm-core-v1; ejecución de Frappe solamente.
2. En rama/tarea de una sola plataforma, revisar AGENTS/pins y baseline; aislar
   sitio/empresa/DB de prueba, probar backup/restauración y cargar por APIs
   soportadas. Implementar producto/Cashea/caja/compras/banco con permisos.
3. Ejecutar todos los escenarios, seis rutas, eventos/MCP, stock/cobros nativos,
   auditoría e idempotencia, incluida concurrencia y recuperación. Repetir con
   el mismo manifiesto en la otra plataforma sin mezclas ni cambios de reglas.
4. Medir con perfil sintético fijo: 1000 productos, 100 clientes, 1000 pedidos
   NEW y 1000 filas bancarias; semilla 100, IDs deterministas y escenario separado
   de los saldos económicos. Por operación seleccionada (búsqueda, stock, creación
   NEW), 20 calentamientos + 1000 muestras seriales, payload idéntico, secuencia
   fija y restauración inicial. Registrar recursos iguales cuando disponibles,
   tiempos crudos, p50/p95/p99 (rango más próximo), consulta/DB y errores. No hay
   SLA ficticio: se comparan observaciones, no se fuerza igualdad de tiempos.
5. Tras estabilizar ambos Core Test, seleccionar un patch oficial posterior
   exacto del mismo major/minor fijado, registrar tags/SHAs/dependencias y congelar
   el objetivo **antes** del ensayo. No modificar ahora pins ni escoger latest.
   Snapshot, actualización/migración aislada, regresión de plataforma + Cencomun,
   captura de cambios y restauración comprobada. Si no existe patch compatible,
   criterio 13 BLOCKED, sin contarlo como aprobado; se puede cerrar el informe
   con esta limitación técnica justificada y los efectos sobre sus conclusiones.
6. Publicar manifiesto, comandos, códigos de salida, evidencia saneada y matriz
   por escenario/criterio/ERP. Informe también setup/build, archivos/LOC propios,
   upstream modificados (objetivo 0), migraciones, llamadas por acción, tests,
   rendimiento, intervención manual, workarounds, huecos de documentación y upgrade.
   Registrar las limitaciones justificadas y cerrar el informe según la política
   siguiente, conservando los mismos datos/oráculo aunque un ERP no pueda ejecutarlos.

| Criterios de ACCEPTANCE_CRITERIA | Evidencia de cierre |
| --- | --- |
| 1. Objetos mediante mecanismos soportados | Puntos de extensión y documentos nativos, incluidos impuesto/contabilidad de TAX01 |
| 2. Core intacto | Hashes/diffs upstream sin modificaciones |
| 3. Permisos en servidor | Matriz LAB: casos permitidos y denegados por API/métodos nativos, también TAX01 |
| 4. Transiciones inválidas rechazadas | Caminos STORE/WEB y rechazo sin cambios parciales de estado/stock/cobros |
| 5. Dinero determinista | Oráculo decimal CO00/CO01/TAX01, comisiones sobre total con impuesto, ingreso/pasivo/gastos separados y redondeo |
| 6. Caja confirmada auditada | Cierre inmutable, actor/instante/cifras preservados y edición silenciosa rechazada |
| 7. Umbrales automatizados | Límites exactos de compras, base LAB, roles y denegaciones |
| 8. Banco idempotente | Importación/reimportación concurrente y conciliación sin duplicaciones |
| 9. API sin DB directa | Seis rutas por mecanismos soportados y errores sin efectos parciales |
| 10. MCP vía adaptador | Servicio externo, equivalencia con API y credenciales mínimas |
| 11. Fixtures cargados | Manifiesto/hash/conteos y lectura de claves esperadas en ambos ERP |
| 12. Búsqueda completa | Conjuntos exactos, paginación completa, empresa/rol y ausencia de duplicación |
| 13. Regresión tras patch | Snapshot recuperable y suites de plataforma + Cencomun tras patch exacto; ausencia de patch compatible -> BLOCKED |
| 14. Setup reproducible | Repetición desde runner limpio/restaurado con instrucciones versionadas y configuración crítica exportable o limitación documentada |

#### Cierre del informe y límites de aprobación

Se permite concluir el informe en uno de dos estados:

- **CERRADO:** todos los escenarios obligatorios ejecutados y resultados
  PASS/FAIL documentados por ERP; 14 criterios evaluados y métricas publicadas.
  Puede haber fallos: cerrar el informe no aprueba automáticamente un ERP.
- **CERRADO_CON_LIMITACIONES:** se ejecutaron los escenarios viables y los
  restantes tienen una limitación técnica justificada y documentada. Sus criterios
  conservan BLOCKED (o FAIL si se comprobó incumplimiento); los casos dependientes
  pueden quedar UNRUN con referencia explícita al bloqueo. Las métricas no obtenidas
  se marcan no disponibles, con motivo, nunca como cero o evidencia de éxito.

Cada limitación debe identificar: ERP/versiones, criterio y escenarios afectados,
condición técnica, comandos/error/evidencia saneada, diagnóstico e intentos
soportados, motivo de persistencia del impedimento, impacto sobre la comparación
y pasos de resolución/verificación para una ejecución posterior. No basta omitir
una prueba por conveniencia ni inventar resultados. Ejemplo: no existe patch
oficial compatible del mismo major/minor -> criterio 13 BLOCKED, documentando
tags consultados y sin forzar una actualización distinta del ensayo acordado.

Publicar por ERP **PASS p/14, FAIL f/14, BLOCKED b/14**, con p + f + b = 14;
los criterios no ejecutados por impedimento justificado se registran BLOCKED.
No excluir bloqueados del denominador ni contarlos como aprobados. Una capacidad
opcional no soportada se señala aparte; una obligatoria no demostrada no es PASS.

La **aprobación del Core Test de cada ERP** exige 14/14 criterios y todos sus
escenarios obligatorios en PASS, sin BLOCKED/UNRUN. Un informe cerrado con
limitaciones puede comparar el subconjunto demostrado, pero no afirmar paridad
integral ni superioridad sobre capacidades sin verificar. Los datos y resultados
esperados siguen idénticos para ambos ERP; una limitación no cambia el oráculo.
Solo se normalizan IDs técnicos,
instantes generados y nombres nativos mediante mapping; dinero, unidades,
permisos, estados/efectos y referencias no se maquillan para obtener paridad.
Serial es opcional donde lo soporte la plataforma; su ausencia no exime búsqueda
obligatoria por código/nombre/referencia. Una evaluación puede concluir que un
ERP no satisface un criterio: se entrega hallazgo y evidencia de fallo, sin
presentar ese ERP como aprobado ni cambiar el oráculo para hacerlo pasar.
No se elige ganador por un solo caso ni por productividad sin corrección ERP.

### 8. Estado y validación de esta entrega

- [x] Conservar las respuestas y detener el cuestionario sin solicitar D04-A.
- [x] Separar confirmado, propuesto LAB y producción aplazada; resolver mapeo por canal.
- [x] Definir escenarios/oráculo y cierre sin implementar Core Test ni modificar Axelor/main.
- [x] Incorporar TAX01-S/TAX01-W con impuesto incluido, contabilidad nativa y
  cierre documentado con limitaciones; mantener bloqueados fuera de aprobados.
- [x] Revisar el plan y recibir autorización explícita de implementación Frappe.
- [x] Materializar/congelar fixtures y ejecutar Frappe en su rama/tarea.
- [ ] Ejecutar Core Test de Axelor y regresión de patch compatible; Frappe publica medición/evidencias y mantiene criterio 13 BLOCKED.

En esta revisión solo se comprobaron fuentes/modelos, coherencia documental,
cálculos esperados, preflight, guardrails y diff. No se ejecutó ningún escenario
de negocio, test de plataforma ni upgrade; la comprobación aritmética de tablas
no es un PASS de ERP. Ese estado **UNRUN** corresponde a la revisión previa. La ejecución autorizada
y sus resultados actuales se publican en reports/frappe-core-test.md y
reports/evidence/frappe-core; no se confunden expectativas con evidencia.

Ante un fallo futuro: 1) conservar primer error y código de salida; 2) identificar
caso/plataforma/impacto; 3) inspeccionar estado y logs saneados; 4) recuperar por
servicios nativos o snapshot probado sin borrar el baseline; 5) repetir el caso
fallido y los afectados; 6) publicar pasos, resultado y limitación sin debilitar
reglas para obtener PASS.

### Anexo — baseline y evidencia previa conservada

La configuración Frappe se comprobó publicada el 2026-10-04: draft_id/revision
nulos, versión 7232c1d2-1a18-4173-adaf-ffc931661ee4~cecfgver_6ac2bfedbf74819cbed3cf34f39c870c,
HEAD ff2a4884da887f15f585f5ec66adc087322d6c78 en lab/frappe-baseline.
Frappe/ERPNext 16.36.1, MariaDB 11.8.6, Redis 8.0.2, Python 3.14.0, Node 24.19.0,
Bench 5.29.0, Yarn 1.22.22 y Cencomun 0.0.1 permanecen fijados. Evidencia integral:
39 comprobaciones + cinco tests en reports/frappe-integral.md y JSON asociado.
Al restaurar, se reiniciaron siete procesos y se verificaron 14 checks HTTP +
cuatro de infraestructura y cinco tests skeleton. Un HTTP 500 inicial fue una
carrera con la disponibilidad de MariaDB, resuelta esperando pong.
Estos son resultados históricos; esta revisión no vuelve a certificar servicios
activos. Axelor validado según el usuario; no se inspeccionó ni modificó su entorno.

Pendiente operativo ya identificado: añadir espera explícita de disponibilidad
a las instrucciones de arranque publicadas; no es una regla de negocio ni fue
aplicada en esta revisión. Se conserva la resolución reproducible:

1. Trabajar en el checkout existente y activar el runtime; Python del sistema
   fuera de `env.sh` no es el Python fijado de Frappe.
2. Iniciar solo los servicios gestionados de este laboratorio.
3. Invocar `wait_ready()` existente: espera hasta 60 segundos por HTTP 200 con
   `pong`. Importar el módulo no ejecuta su prueba de reinicio.
4. Ejecutar las 14 pruebas HTTP y las cuatro de infraestructura con el
   intérprete de Bench. Un fallo tiene que conservar su código de salida.
5. Si la espera falla, consultar privadamente el log del servicio afectado en
   `/workspace/.local/frappe-integral/logs/`, resolver el primer error y repetir
   la espera y las comprobaciones. No publicar logs ni credenciales, no forzar
   recreación del sitio y no desactivar permisos, TLS o verificación de hashes.

```sh
cd /workspace/cencomun-erp-lab
set -euo pipefail
source scripts/frappe-integral/env.sh
python scripts/frappe-integral/services.py start
/workspace/.local/frappe-integral/bench/env/bin/python - <<'PY'
import importlib.util
from pathlib import Path
path = Path('scripts/frappe-integral/validate_restart.py')
spec = importlib.util.spec_from_file_location('ccm_restart_readiness', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.wait_ready()
print('Site ready: HTTP 200 / pong')
PY
/workspace/.local/frappe-integral/bench/env/bin/python scripts/frappe-integral/validate_http.py after
/workspace/.local/frappe-integral/bench/env/bin/python scripts/frappe-integral/validate_infrastructure.py after
```

### Anexo — análisis de plantilla conservado

Fuente analizada: `Cargar_Productos-20261002-185552.xlsx`, hojas
`Instrucciones` y `Tecnología - Accesorios`; SHA-256
`3b5c2d67b8bd6bdb2c7232f7dee1316ab584fba60bf3015b260257b5092fea16`.
Se revisaron celdas, validaciones, rangos e imágenes. El archivo y su registro
comercial no se incorporan al repositorio ni se utilizan como fixtures; solo
se documentan los hechos de formato necesarios para los requisitos del usuario.
Las instrucciones de completar/guardar/subir el archivo se leen como guía de
la plantilla: no cambian el encargo de análisis y planificación.

| Tema | Hecho observado y localización | Consecuencia para el plan |
| --- | --- | --- |
| Precio | F3 indica Precio (USD); F6:F105 admite números decimales desde 0 | La plantilla solo demuestra el formato. El usuario después confirmó precio final con impuestos incluidos, máximo dos decimales y rechazo de cero en venta ordinaria; la excepción de accesorios se aplazó |
| Condición | N6:N105 enumera Nuevo, Usado, Reacondicionado | Se elimina la pregunta por el catálogo Cashea; usar mapeo explícito NEW/USED/REFURBISHED |
| Garantía | O3/O5 representan cantidad; O6:O105 valida enteros desde 0. P3/P5/P6:P105 representan unidad Dias, Meses, Años | El usuario confirmó cantidad + unidad y 0 = sin garantía; ADR-003 sustituye warranty_months y prohíbe pérdida de la unidad original |
| Estado | T5 describe Activa como visible en marketplace, Pausada como oculta allí pero conservada en inventario; T6:T105 contiene ambas opciones | El usuario después confirmó que financiación en tienda y visibilidad son independientes; Pausada no impide por sí sola financiar |
| Variantes | D:G agrupa SKU, Stock, Precio e Imágenes por variante; T5 indica que Estado aplica a todas las variantes | No confundir una autorización de financiación por producto con el estado compartido de publicación; no agregar ahora un proyecto de variantes |
| SKU | D3/D5 identifican SKU y máximo de 40 caracteres | supplier_reference no aparece en la plantilla; el usuario confirmó conservar SKU y referencia por separado cuando sean distintos |
| Stock | E3/E5/E6:E105: números enteros desde 0 | No inferir reglas de disponibilidad, reservas o venta sin stock; tampoco limitar automáticamente qty de pedidos por una validación de esta columna |
| Cuotas | M3/M5/M6:M105: máximo hasta 3, 6, 9 o 12 cuotas sin interés | Es el máximo de cuotas del producto; no informa comisión al comercio, anticipo ni liquidación de pedidos |
| Enviable | L3/L5/L6:L105: Si/No | Indica elegibilidad de envío; no define tarifa, responsable del costo ni obligaciones de despacho |
| Otros datos | Imágenes G5: URLs separadas por pipe, primera principal; título Q5 máximo 256; descripción R5 texto plano máximo 5000, sin HTML/emojis; H:K peso kg y dimensiones cm | Registrar como formato de una posible exportación futura; no ampliar el Core Test con carga masiva, imágenes o logística ahora |

Las filas 3–5 contienen encabezados, obligatoriedad e instrucciones. La fila 6
es la única con datos de producto ingresados; las posteriores contienen
selectores/predeterminados, no un catálogo de mil productos. La obligatoriedad
indicada en la fila 4 no está garantizada por Excel: muchas validaciones permiten
blancos. No se probó la aceptación/rechazo del backend de Cashea.

**Problema de la copia analizada:** reglas coherentes para carga aparecen en
las filas 6–105; desde 106 hay listas con `#REF!`, validaciones numéricas en
columnas de imágenes/texto/selectores y pérdida de las listas de condición y
estado. Es un defecto del archivo, no una regla de negocio ni una demostración
de que Cashea limite las cargas a cien productos. No se alteró el original.

Resolución propuesta antes de usar esta copia para una carga real:

1. Conservar el original y descargar una plantilla nueva de la misma categoría
   desde Merchant Web; comprobar si el defecto se repite.
2. Revisar en Datos -> Validación de datos los rangos de A, E, F, L, M, N, O,
   P, Q, R y T, especialmente la frontera entre filas 105 y 106. Comparar con
   los encabezados vigentes; no confiar en las reglas desplazadas.
3. Si hay que reparar una copia, extender solo las validaciones correctas de
   cada columna al rango requerido y eliminar reglas inválidas/superpuestas.
   Conservar valores, fórmulas, formatos y estructura de carga. No reemplazar
   columnas enteras copiando contenido de una fila de producto.
4. Verificar en la copia filas 6, 105, 106 y la última fila utilizada: listas
   completas, garantías/stock enteros, precio numérico y límites de texto, sin
   referencias rotas. Revisar aparte todos los campos obligatorios.
5. Antes de publicar productos reales, validar con el mecanismo de
   previsualización/validación que ofrezca Merchant Web; si no existe, acordar
   una prueba controlada con el usuario. Esta tarea no autoriza subir productos.

### Registro de implementación autorizada — ADR-010

El usuario aprobó este ExecPlan y sus supuestos exclusivamente de laboratorio,
autorizando implementar y ejecutar Frappe en lab/frappe-baseline. Axelor, main y
producción no están autorizados para modificación. Se conserva todo el alcance,
las tablas y los anexos anteriores. Las evidencias finales distinguen PASS, FAIL,
BLOCKED y UNRUN; el criterio 13 no se aprueba por resultados anteriores al patch.

Detalles sintéticos de ejecución exportados, sin decisiones de producción:
- CBANK es una tercera contraparte ficticia para los cobros bancarios no aplicados;
  evita contaminar el saldo cero de C002. Importes/referencias BK001–004 no cambian.
- Los escenarios usan almacenes independientes WH-LAB-001-<caso>, ligados al
  mismo identificador funcional en el mapping. Se normalizan sufijos nativos.
- El benchmark usa IDs por muestra deterministas, con todos los demás valores
  de negocio iguales; así mide creaciones reales y no respuestas idempotentes.
- El serial de búsqueda no tiene almacén ni demuestra seguimiento físico serial.
- Los grupos se agregan al criterio mediante la peor evidencia obligatoria;
  una repetición corregida conserva el fallo previo en el registro de intentos.

Las instrucciones y el runner se conservan en scripts/core-test/README.md.

Resultado Frappe: 28 grupos PASS; 13/14 criterios PASS, 0 FAIL, 1 BLOCKED
(patch compatible pendiente). Casos de patch UNRUN. No aprobación integral
14/14 ni resultados nuevos de Axelor. Véase reports/frappe-core-test.md.

### Corrección acotada autorizada de cobertura — revisión 2

El usuario solicitó corregir auditoría y comprobar omisiones concretas. El
resultado anterior de 28 grupos es histórico; no acredita estas aserciones
añadidas. El oráculo económico, los importes y las reglas LAB aprobadas no cambian.

- [x] Registrar y validar semánticamente actor/fecha/objeto/motivo/correlación y
  JSON antes/después de estados, aprobación/revisión, caja, tasa y conciliación.
- [x] Rechazar estados desconocidos, entrega sin aceptación y WEB sin guía,
  comprobando igualdad de snapshots nativos; cancelar desde APPROVED y PREPARING
  mediante cancelación nativa, sin salida, factura ni pago.
- [x] Denegar a MCP aprobación, entrega/despacho, liquidación, caja, tasa manual
  y conciliación sobre objetos elegibles; comprobar auditoría y ausencia de efectos.
- [x] Comparar el resultado completo API/MCP de las seis rutas, incluyendo
  creaciones y reintentos en ambos sentidos. Solo se excluye metadata de transporte;
  replay se comprueba por separado y los IDs nativos deben ser iguales.
- [x] Entregar un evento con éxito, verificar un efecto, reiniciar el consumidor,
  comprobar persistencia y repetir el mismo evento: dos recepciones, una aplicación.
- [x] Reejecutar suites afectadas y copia restaurada, regenerar evidencias y matriz.

El suplemento LAB y el contrato de 34 grupos obligatorios se versionan en
`fixtures/ccm-core-v1/coverage-required.json` y su SHA256 en el manifiesto. Los
fixtures anteriores conservan sus bytes. Caso ausente o evidencia de revisión
anterior quedan UNRUN; fallos y bloqueos nunca se convierten en PASS. La revisión
2 exige además nueva reproducción de las suites nativas. El bloqueo del patch y
la limitación de la suite oficial se conservan sin cambios de alcance. PR borrador;
sin modificar main, producción, Axelor o upstream.

Ejecución de revisión 2: 34 grupos PASS, ocho negativas MCP con ocho auditorías
de denegación y cero efectos de éxito, ocho pares equivalentes API/MCP, 109
comprobaciones semánticas de auditoría y 28 eventos con dos recepciones pero una
aplicación tras reiniciar el consumidor. La copia restaurada repitió 13 grupos
de negocio y cinco de finanzas. El criterio 13 permanece BLOCKED y sus seis
escenarios UNRUN; la matriz final es la publicada en el informe.
