# Piloto Axelor v1 — estado de validación

Trabajo en curso; **no se declara aceptación E2E completa**. Base inmutable
`bc0183ea6fd40ea97d6be5c11ce0db0c00b5d35a`; evaluación histórica y sus 2 FAIL
no modificados. Rama exclusiva `pilot/axelor-v1`. AOS 9.1.8 / AOP 8.2.3,
Java 21 y PostgreSQL 16.15; pins y locks conservados.

| Escenario | Estado comprobado hasta este punto |
|---|---|
| Rama nueva desde referencia, preflight y guardrails | PASS |
| Compilación full-stack / WAR con locks sin actualización | PASS |
| Unitarios/modelos Java | PASS, 61 casos en revisión más reciente |
| Procesamiento de evidencia Core | PASS, 93 casos |
| Acceso loopback real con Chromium y login | PASS |
| URL accesible para el usuario / alojamiento persistente | BLOCKED: falta destino autorizado; no preview expuesto |
| Diez productos, tres clientes, stock nativo inicial | PASS en lectura después del commit |
| Menús y apertura de sesión por supervisor | PASS desde UI |
| Venta de varias líneas por operador | PASS desde UI y lectura posterior |
| Inicial Cashea antes de entrega | PASS: 30 USD cobrados, 45 financiados pendientes, sin entrega/factura |
| Esperado en caja con inicial aún no entregada | PASS: 105 USD = 75 contado + 30 inicial Cashea; financiado excluido |
| Operador intenta cancelar | PASS de denegación explícita de perfil |
| Control de costo positivo y rechazo negativo nativo con extensión | PASS en runtime; no sustituye FAIL histórico |
| Rollback de entrega fallida | PASS: sin factura/salida/costo; presupuesto finalizado y stock intactos |
| Entrega y conciliación de anticipo | FAIL observado por colección nativa de pagos nula; corrección y regresión añadidas, reintento pendiente |
| Liquidación Cashea, envío, devolución al cancelar, cierre inmutable, replays, aislamiento | UNRUN completos |
| Regresión Core full-stack completa de 34 grupos en esta rama | UNRUN |

Las pruebas UI se ejecutan con Playwright + Chromium sobre el WAR y PostgreSQL,
no una simulación de frontend. La evidencia final se publicará sólo después de
las lecturas de comprobación y saneamiento de logs. Ver la guía y restricciones
en `labs/axelor/pilot/README.md`. La falta de servidor no detiene las pruebas locales.
