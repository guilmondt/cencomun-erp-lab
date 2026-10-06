# Piloto Axelor v1 (laboratorio)

Estado: implementación en validación. No desplegar como producción ni presentar
los escenarios sin evidencia como aprobados. Evaluación histórica inmutable:
`bc0183ea6fd40ea97d6be5c11ce0db0c00b5d35a`; código probado entonces:
`a2f462f67526af94409bd050bf277d78f4782387`. Sus dos FAIL nativos se conservan.

## Funcionamiento previsto

Menú **Cencomun · Piloto**: Productos e inventario, Venta y pedido,
Entrega y liquidación, Cierre de caja. Operador registra/entrega; supervisor
puede además cancelar, liquidar y cerrar. Las validaciones se ejecutan en el
servidor. Los permisos de escritura genérica no autorizan mutar los registros
del flujo: los repositorios exigen el servicio propio.

1. Supervisor abre la sesión de caja.
2. Operador introduce varias líneas de producto y unidades enteras; elige contado
   o Cashea, tienda o web, financiado y envío absorbido. **Registrar pedido** guarda
   un presupuesto nativo finalizado y reservas propias de cantidades. La interfaz
   no lo presenta como pedido nativo confirmado. No hay cobro ni salida de stock.
3. **Registrar cobro inicial real** se usa cuando efectivamente se cobra, antes o
   después de entregar. Genera un PaymentVoucher nativo; antes de facturar queda
   como crédito no aplicado del cliente y ya forma parte del efectivo de su sesión.
4. **Entregar productos** confirma, entrega, factura y aplica por conciliación el
   recibo que ya exista, sin cobrar otra vez. En web se exige guía. Los pendientes
   de cobro permanecen pendientes. Supervisor puede cancelar antes de entregar;
   si ya se cobró la inicial, **Cancelar y devolver inicial cobrada** registra una
   devolución real mediante voucher y concilia ambos recibos. No usar ese botón
   si aún no se ha devuelto físicamente el dinero.
5. Supervisor registra la liquidación Cashea posteriormente. Comisión: 4% tienda
   o 6% web sobre productos con impuesto, más 4% financiado. El envío se descuenta
   una sola vez como gasto separado; no altera costo ni se vuelve a cobrar inicial.
6. Supervisor consulta esperado, introduce efectivo contado y explica diferencias.
   Confirma un cierre inmutable. El saldo Cashea pendiente y transferencias bancarias
   no forman parte del efectivo. La fuente son líneas nativas de recibos/devoluciones
   de esa sesión, incluso si todavía no hay entrega ni factura.

## Supuestos de laboratorio y límites pendientes de validación

- Sólo datos ficticios, USD, una caja/empresa/almacén, fecha fija 2026-10-01,
  IVA sintético 10%; ninguna afirmación de validez fiscal venezolana.
- Diez productos y tres clientes. Varias líneas, sin duplicar producto en un mismo
  pedido; se aumenta su cantidad entera en la línea existente.
- El precio se obtiene del catálogo en servidor e incluye impuesto; no se
  aceptan descuentos manuales ni precios enviados por el navegador.
- Garantía conserva cantidad y unidad originales, sin convertir meses/años a días.
- El momento del cobro lo indica el operador con una acción separada; no se presume
  ninguna política habitual de Cencomun. La inicial prevista es total menos financiado.
- No cancelación posterior a entrega ni liquidación con transferencia neta negativa.
- Confirmado el cierre no admite nuevos cobros/devoluciones en esa sesión.
  Entrega sin nuevo cobro y liquidación bancaria no modifican el efectivo cerrado.
- Reservas: extensión Cencomun sobre cantidades de stock nativo, serializada por
  compañía; impide sobreasignar entre pedidos del piloto. No son estados ni reservas
  nativas ficticias. El flujo nativo vuelve a verificar stock al entregar.
- Cancelación nativa sólo de presupuesto. Se confirma al entregar, a diferencia del
  Core histórico que confirmó antes y conserva su FAIL de cancelación.
- Las cuentas automáticas requieren `CCM_PILOT_EPHEMERAL=1` y secretos aleatorios
  externos al repositorio. No habilitarlas en servidor persistente sin autorización.

## Acceso y despliegue propuestos

Este entorno no expone una URL de vista previa alojada. El harness
`LoopbackTomcat.java` utiliza la API pública de Tomcat fijada por el host, escucha
únicamente en `127.0.0.1:18080` y despliega el WAR, sin cambiar upstream.
La base de pruebas desechable se publica sólo en `127.0.0.1:15432`.
Son comprobaciones locales, no una dirección accesible desde el equipo del usuario.

Servidor propuesto (pendiente de autorización/destino): Linux x86_64, 4 vCPU,
8 GB RAM, 40 GB libres. JVM aplicación 3 GB; compilación JVM hasta 3 GB, más
PostgreSQL y sistema. Compilar fuera del servidor reduce ese pico.
Usar las imágenes y herramientas fijadas en `../ci/pins.sh`, Java 21, AOS 9.1.8,
AOP 8.2.3 y locks existentes; verificar SHA del WAR y commit antes de desplegar.

Acceso inicial: túnel SSH hacia la aplicación loopback. Sólo requiere el puerto
SSH ya autorizado; no publicar PostgreSQL, 8080 ni un panel Docker. El destino,
usuario SSH y mecanismo de credenciales deben gestionarse por el canal seguro
del entorno; no enviar contraseñas o tokens al chat. No se ha instalado servidor
externo ni contratado alojamiento.

Persistir PostgreSQL, uploads y configuración privada fuera de la imagen.
Propuesta inicial: copia diaria `pg_dump -Fc`, archivos subidos y manifiesto
(commit/SHA/versiones), siete copias diarias, copia cifrada fuera del host mediante
un destino autorizado. Antes de habilitar acceso persistente: restaurar una copia
a DB y uploads aislados, verificar saldos/stock/cierres, probar reinicio, sustituir
cuentas iniciales por credenciales aprobadas y limitar la red. No usar el runner
CI histórico para alojamiento: destruye sus contenedores al terminar.

## Evidencia requerida

Revisar `reports/axelor-pilot-v1-status.md`. PASS de compilación o tests de modelos
no sustituye E2E. En revisión coordinada se deben ejecutar los cinco pasos con
ambos perfiles, repetir clic/recarga/reingreso, probar denegaciones servidor y
comparar inventario, facturas, pagos, comisiones, envío y cierre después del commit.

## Regresión por navegador

`ui-regression.py` usa Chromium/Playwright contra el WAR real y requiere una
base **nueva y desechable**, preparada con `ccm-pilot-prepare` y `ccm-pilot-seed`.
Configure `CCM_PILOT_DISPOSABLE=1`, `CCM_PILOT_ACTORS_FILE` (JSON privado con
claves operator/supervisor), `CCM_PILOT_RESULTS` y, si procede, `CCM_PILOT_URL`.
No lo ejecute sobre una sesión con trabajo previo. No imprime contraseñas.
Los formularios nativos reabiertos requieren el lápiz **Editar** para introducir
guía, motivo o efectivo contado; los datos económicos guardados siguen bloqueados.

Al actualizar vistas sobre una DB existente, la restauración nativa de metadatos
puede invalidar asociaciones/cache de perfiles. Reaplique la preparación del
piloto y reinicie/reingrese antes de probar permisos. No restaure metadatos durante
una sesión operativa. Las cuentas del piloto tienen una lista exacta de acciones
permitidas; las acciones administrativas y cadenas arbitrarias quedan rechazadas.

El impuesto se redondea por línea y se suma mediante la política confirmada.
La extensión de comprobación de factura exige igualdad exacta y asiento equilibrado;
`allowedTaxGap` permanece en cero. El diagnóstico con tolerancia de un centavo
fue descartado y no constituye política ni aceptación.
