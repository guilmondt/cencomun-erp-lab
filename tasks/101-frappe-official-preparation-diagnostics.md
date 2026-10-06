# ExecPlan — fallos de preparación oficiales desde 8158b68

Encargo autorizado por el usuario, 2026-10-05 America/Los_Angeles. Solo
`lab/frappe-baseline`. Conservar los completos Frappe/ERPNext FAIL, criterio 13
BLOCKED y seis PATCH UNRUN. No repetir restauración cloud, Guardar/Publicar,
suites completas, modificar pins, oráculo, upstream, main, Axelor o producción.

1. Conservar configuración saneada, fixtures oficiales fijados y Error Log
   existentes de tasas. Distinguir configuración deshabilitada de excepciones
   del proveedor/proxy; no deducir causa a partir de cero. Correlacionar los
   cinco errores payment_request, declarando límites de los registros antiguos.
2. Crear dos sitios oficiales vacíos marcados `*-diagnostic.test`, conservando
   los sitios usados. Prepararlos con hooks/bootstrap nativos de CI. Cada
   reproducción usa proceso nuevo; el lock rechaza suites simultáneas.
3. Ejecutar módulos/métodos acotados con transporte externo prohibido. El
   observador registra exclusivamente estado nativo permitido, no sustituye
   cálculos, fixtures, validadores, autenticación ni respuestas del proveedor.
   La restricción de transporte se etiqueta; no reproduce un HTTP externo real.
4. Payments: comparar apps.txt/modules.txt/mapa y caché antes/después de los
   módulos precedentes en el mismo proceso CI nativo y en proceso nuevo. No
   purgar caché ni corregir resolvedor sin demostrar una preparación incorrecta.
5. Autenticación: CI nativa en sitio limpio, observar respuesta HTTP y separar
   request=None residual. Cambiar solo preparación local demostrada; no omitir
   aserciones ni poner resultados esperados en el transporte.
6. Aislar BOM 0/10, cantidad Routing cero y Basic Rate negativo con sus fixtures
   oficiales y validador intacto. Diferenciar errores FX de divisiones de
   fabricación. Detener la línea al pasar o demostrar el límite; lo desconocido
   sigue desconocido.
7. Si faltan fixtures oficiales necesarios, cargar exclusivamente sus registros
   exactos mediante helpers nativos, documentar hashes/fechas y comparar antes/
   después. No inventar tasas ni usar tasas LAB ni relajar reglas de vigencia.
8. Conservar cada intento y publicar solo código/documentación/evidencia
   saneada. Repetir Cencomun si se modifica su runtime; si todo queda en Bench
   copiado, demostrar ese aislamiento. Checks, checkpoint/push solo lab y PR #4
   borrador. No presentar un PASS modular como PASS del completo.

Finalización: cada línea tiene resultado ejecutado o límite demostrado, o un
pendiente desconocido identificado con siguiente reproducción concreta. No
convertir desconocido en bloqueo inevitable ni aprobar cobertura no ejecutada.
