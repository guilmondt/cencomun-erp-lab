# Piloto Axelor v1 — estado comprobado

Actualización 2026-10-06. **Acceso externo BLOCKED**: no hay servidor autorizado
conectado ni URL de preview para el usuario. Chromium sí ejecuta el WAR en
`127.0.0.1:18080`, PostgreSQL sólo en loopback. No se amplió red ni permisos.
PR borrador #5; no merge ni producción.

La [cohorte v5](evidence/axelor-pilot/2026-10-06/acceptance-v5) ejecutó aplicación
`8df643dc2203750f8be3f7e8907a90d3cba35682`, WAR
`89322f1b5d82122a1de5c8ff70f14cb0cba88b5bab67b8ab4e26fa2cc4eca400`.
Los verificadores reforzados corresponden a `4f09807944ae481fc60df9adda98414b80e2879b`.
Una recompilación y regresión del Core del SHA final está en curso; **los
resultados de versiones previas no se atribuyen a ese nuevo WAR**.

| Escenario v5 | Resultado y evidencia |
|---|---|
| Contado, 2 productos, entrega antes de cobro | PASS UI; 75 USD, factura pagada; supervisor no ve liquidación Cashea en contado entregado |
| Cashea tienda, inicial antes de entregar, liquidación posterior | PASS UI/nativo; 75 total, inicial 30, financiado 45, comisión 4,80 y transferencia 40,20 |
| Cashea web, inicial después de entregar | PASS UI/nativo; 90 total, inicial 36, financiado 54, comisión 7,56, envío separado 2, transferencia 44,44; costo 45 |
| Redondeo por línea | PASS; bases 36,36 + 45,45, impuesto 3,64 + 4,55, total 90; asiento equilibrado y tolerancia nativa cero |
| Impuesto alterado 0,01/0,02 y asiento descuadrado | PASS de rechazo en pruebas Java de la extensión; no se presenta como prueba HTTP |
| Cashea pendiente sin entrega | PASS; inicial real 24, financiado 36 fuera de caja, sin factura/salida; visible en pendientes |
| Cancelar antes de entrega con inicial cobrada | PASS UI/nativo; devolución 28, presupuesto nativo cancelado, sin factura/salida/costo |
| Cierre | PASS; esperado 165 = 75+30+36+24+28−28; contado 164, diferencia −1 explicada; sin motivo se rechazó |
| Replays, inmutabilidad y negativas servidor | PASS: snapshots antes/después iguales de 15 modelos, estados/importes/referencias/pertenencia; `verify-native.py` ejecutado después |
| Ambos perfiles, catálogo y existencias | PASS; catálogo sin Nuevo/Editar, P001 stock físico 18 y costo medio 30; reingreso a cierre conserva 164 |
| Aislamiento | PASS: búsqueda y lectura directa de centinelas externos reales denegadas para ambos perfiles, tres reingresos cada uno |
| Backup/restauración | PASS; `pg_dump -Fc` restaurado en DB distinta; once tablas económicas con conteos y hashes iguales |
| Acceso del usuario/servidor persistente | BLOCKED; destino/acceso aún no conectado ni autorizado para instalar |

La UI se ejecutó por etapas con Playwright/Chromium. Se conservaron los errores
del guion y los intentos rechazados; no se duplicaron ventas al continuar.
Ver `refs.json`, `receipts.json`, `network-actions.json`, `native-verification.json`,
`server-replays.json`, `views.json`, `restore.json` e `isolation.json` en v5.
El fallo del primer verificador de snapshots está conservado; su snapshot inicial
también coincide con el snapshot final. Los resultados v3/v4 se publican por
separado y no sustituyen los controles de campos de v5.

## Regresión histórica, separada del piloto

CI [37524117138](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37524117138),
commit **2e33cca**, terminó `failure`/salida 2. La evidencia completa recuperada
con el extractor existente y 103 archivos verificados por hash confirma **32 PASS
/ 2 FAIL**, también repetidos. Fallos: `VAL01-04` (acepta costo negativo nativo)
y `STATE-CANCEL-BEFORE-HANDOVER` (rechaza cancelación nativa de pedido confirmado).
**Cero grupos fallidos adicionales.** Es evidencia del commit indicado, no del
SHA final. La descarga ZIP dio 403; se usaron los avisos completos de los logs
autorizados, sin ampliar acceso. Ver [clasificación](evidence/axelor-pilot/2026-10-06/ci-37524117138/classification.json).

La referencia `bc0183ea6fd40ea97d6be5c11ce0db0c00b5d35a`, código histórico
`a2f462f67526af94409bd050bf277d78f4782387`, contrato/oráculo/fixtures, pins,
upstream y resultados históricos permanecen intactos.
