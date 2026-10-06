# Piloto Axelor v1 — estado comprobado

Actualización 2026-10-06. **Acceso externo BLOCKED**: no hay servidor autorizado
conectado ni URL de preview para el usuario. Chromium sí ejecuta el WAR en
`127.0.0.1:18080`, PostgreSQL sólo en loopback. No se amplió red ni permisos.
PR borrador #5; no merge ni producción.

La **cohorte v6** ejecutó desde una base nueva las cinco operaciones por UI,
sin reanudar etapas. Aplicación `753728b3859ec0077c1294ae48b330edc320f6e3`, WAR
`35efd7ccbcc6270cf7758f19403500fe7848cdbcc83cb3ee9b972f7f7031cf9e`,
verificadores `fb3f0d8f8b622e1db8b7fb19aaf8a09ab0e1a546`.
[Evidencia completa de piloto](evidence/axelor-pilot/2026-10-06/acceptance-v6).
El resultado corresponde a Chromium local; no demuestra alojamiento externo.

| Escenario v6 | Resultado y evidencia |
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
| Ambos perfiles, catálogo y existencias | PASS; catálogo sin Nuevo/Editar, P001 stock físico 18 y costo medio 30; reingreso y recarga en ambos perfiles conservan 164 y snapshots completos idénticos |
| Aislamiento | PASS: búsqueda y lectura directa de centinelas externos reales denegadas para ambos perfiles, tres reingresos cada uno |
| Backup/restauración | PASS; `pg_dump -Fc` en DB distinta; once tablas con hashes iguales; aplicación restaurada arrancada y probada por navegador/nativo, snapshots iguales |
| Acceso del usuario/servidor persistente | BLOCKED; destino/acceso aún no conectado ni autorizado para instalar |

La UI v6 terminó en una sola ejecución. Se registró el rechazo esperado
**“Explain the cash difference before confirming”** al cerrar sin motivo,
seguido del cierre con motivo. Snapshots de 15 modelos antes/después de
replays/negativas y después de reingreso/recarga:
`dddb6fce457feeadd3948291e494df5f1b0f96ad774a316e245fc34dc5714775`.
La lectura nativa de documentos/saldos se ejecutó después de las negativas.
Ver `execution.json`, `receipts.json`, `network-actions.json`,
`native-verification.json`, `server-replays.json`, `views.json`, `restore.json`
e `isolation.json`. Las versiones previas v2–v5 y sus errores de guion,
diagnósticos y comprobaciones se conservan por separado en `cohorts.json`.
Ningún resultado anterior sustituye las comprobaciones v6.

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


## Regresión nativa de la fuente final

Fuente **753728b**, WAR **35efd7cc…**: **32 PASS / 2 FAIL**, sin nuevos fallos;
los mismos `VAL01-04` y `STATE-CANCEL-BEFORE-HANDOVER`. Piloto desactivado,
base nueva, reinicio real de aplicación y PostgreSQL y recuperación durable
comprobados. Build verificado PASS y diffs upstream cero.
[Archivo completo](evidence/axelor-pilot/2026-10-06/core-final/complete-native-evidence.tar.gz)
con 48 JSON, manifiesto de hashes, cobertura y recibo de reinicio.

Los 14 criterios históricos resultan **6 PASS / 4 FAIL / 3 UNRUN / 1 BLOCKED**.
No se ejecutaron en esta cohorte el benchmark congelado, una segunda ejecución
completa aislada ni la restauración Core; la restauración del piloto se identifica
por separado. La actualización de versión sigue BLOCKED por decisión previa.
Esto no cambia el resultado ni el alcance de la evaluación histórica.

El [primer intento](evidence/axelor-pilot/2026-10-06/core-final-attempt1)
conserva **30 PASS / 3 FAIL / 1 UNRUN**: además de los dos fallos conocidos,
`TAX01-S-NATIVE` falló porque los mismos registros de stock se leyeron en otro
orden. La comparación campo por campo identifica ese único cambio de orden.
Se corrigió el lector propio para ordenar por ID, sin modificar contrato ni
comparador. La regresión Java también comprueba que un cambio real de costo
sigue siendo detectable. El siguiente caso nativo pasó desde una base nueva.

Compilación final: **64 tests Java del módulo + 16 upstream, 93 Python Core y
2 Python de evidencia PASS**; logs y XML en
[build-final](evidence/axelor-pilot/2026-10-06/build-final). Se conserva el intento
offline de upstream fallido por dependencias no cacheadas y su repetición exitosa
con las versiones fijadas.


## Entrega y acceso pendiente

PR borrador [#5](https://github.com/guilmondt/cencomun-erp-lab/pull/5), rama
`pilot/axelor-v1`. [Guía corta y despliegue](../labs/axelor/pilot/README.md).
La instancia local queda sobre la copia restaurada de la aceptación, con cierre
confirmado. Para otra sesión operativa se necesita una base nueva; no se reabre
ni altera el cierre. Los backups/credenciales están fuera del repositorio.

Falta destino SSH autorizado y conexión segura al servidor del usuario para
instalar y comprobar acceso desde su equipo. Propuesta: Linux x86_64, 4 vCPU,
8 GB RAM, 40 GB libres; WAR verificado, PostgreSQL/archivos/configuración
persistentes, backup privado y prueba de restauración. Acceso inicial por túnel
SSH existente, aplicación/DB en loopback, sin puertos públicos adicionales.
No se instalaron servicios ni accesos persistentes externos.
