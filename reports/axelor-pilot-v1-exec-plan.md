# Axelor piloto v1 — plan de ejecución

Fecha: 2026-10-06. Rama exclusiva `pilot/axelor-v1`, creada tras comprobar
su ausencia local y remota desde `bc0183ea6fd40ea97d6be5c11ce0db0c00b5d35a`.
Código históricamente probado: `a2f462f67526af94409bd050bf277d78f4782387`.
Contrato, fixtures, oráculo y evidencias históricas se conservan sin cambios;
32 PASS / 2 FAIL nativos no se reinterpretan como éxito del piloto.

## Secuencia

1. Verificar entorno y acceso: Docker, Java 21, Chromium disponibles;
   bind en loopback probado. No hay preview/publicación soportada expuesta.
2. Construir extensiones propias y vistas Axelor. Separar cobro inicial de
   liquidación, cierre con fuentes reales y fecha/sesión; autorización servidor,
   idempotencia, inmovilidad del cierre confirmado, costos no negativos.
3. Ejecutar regresión Core afectada, controles nativos y navegador real con
   operador/supervisor. Registrar PASS/FAIL/BLOCKED/UNRUN por escenario.
4. Conservar logs saneados y SHA; publicar sólo esta rama y PR borrador.
   Despliegue persistente externo requiere destino autorizado por el usuario.

## Supuestos y límites propuestos antes de declarar operabilidad

- Datos exclusivamente ficticios; un establecimiento y caja; moneda USD,
  fecha de laboratorio 2026-10-01, impuesto sintético del 10%, no fiscal.
- El nativo sólo cancela presupuestos borrador/finalizados. Para poder cancelar
  antes de entrega, el piloto mantendrá el documento nativo finalizado hasta
  entregar; confirmación + entrega constituyen una operación transaccional.
  No se presentará un pedido nativo confirmado como cancelado ni se alterará
  un estado nativo a mano. Esta restricción pasó UI y comprobación nativa en v6 (ver matriz).
- Revisión de alcance: múltiples líneas; cobro real independiente de entrega, mediante
  PaymentVoucher nativo no aplicado y conciliación posterior a factura. La propuesta
  inicial de un solo producto/cobro al entregar fue retirada antes de aceptación.
- Alojamiento propuesto: Linux x86_64, 4 vCPU, 8 GB RAM, 40 GB disco. Java
  necesita hasta 3 GB y compilación hasta 3 GB, más DB/SO. Acceso por túnel SSH,
  aplicación loopback y DB interna; sin nuevos puertos públicos.
- Persistir PostgreSQL y uploads; backup pg_dump + uploads + manifiesto de
  versión, copia cifrada fuera del host por medio autorizado y restauración
  probada antes del uso. Retención inicial propuesta 7 copias diarias.
- No crear cuentas persistentes ni instalar un servidor externo sin aprobación.

## Verificación inicial (registro histórico)

- Preflight y 22 tests existentes: PASS, build 15 s, verify-repo PASS.
- No `.agents/skills` existente en repositorio ni `/workspace/.agents`.
- No runtime WAR compilado en el entorno guardado. Compilación full-stack y
  acceso navegable aún pendientes. Docker disponible no demuestra hosting.

## Avance comprobado

Las extensiones y las cuatro áreas operativas están implementadas. La matriz
[de resultados](axelor-pilot-v1-status.md) identifica cohortes y artefactos,
incluidos errores de guion y diagnósticos descartados. El acceso Chromium
local está probado; el acceso externo continúa bloqueado por falta de destino
y autorización de instalación. PR borrador #5, sin merge.


## Cierre de la implementación local

- Extensiones, cuatro áreas UI y cinco escenarios: PASS en cohorte v6 desde cero.
- 64 pruebas Java del módulo, 16 upstream, 93 Python Core y 2 de evidencia: PASS.
- Core nativo final, con reinicio real: 32 PASS / 2 FAIL históricos; criterios
  6 PASS / 4 FAIL / 3 UNRUN / 1 BLOCKED. No se convierte en aceptación histórica total.
- Replays/negativas, snapshots completos, recarga/reingreso, aislamiento y
  restauración con nuevo arranque/navegador: PASS.
- Evidencia de errores anteriores preservada y clasificada; sin cambios de
  contrato, oráculo, fixtures, pins, upstream ni referencias históricas.
- Entrega externa: BLOCKED por falta de conexión/autorización del servidor.
  No hay otra implementación local pendiente para los escenarios aceptados.
