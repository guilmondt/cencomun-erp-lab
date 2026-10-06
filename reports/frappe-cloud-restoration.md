# Restauración cloud del snapshot Frappe fcf690d

**PASS externo aportado por el coordinador.** Este agente incorporó el JSON
recibido y comprobó su consistencia con las identidades y datos esperados. No
ejecutó esas pruebas en la tarea externa ni las repitió en esta instancia.

- [Tarea cloud nueva](https://chatgpt.com/local/01a10f0a-cbb7-7157-82d5-b74c039a0032),
  turno `01a10f18-3fcb-7303-b012-78b5b98e5e5b`.
- [JSON exacto del coordinador](evidence/frappe-cloud/restoration-fcf690d-external.json).
- [Atribución, hash y límites](evidence/frappe-cloud/restoration-fcf690d-attribution.json).
- SHA256 del JSON: `2c86f345b0ab9c545a21be3f28b164e85becf98094fea55b98dc536965f1e7c0`.

| Comprobación reportada | Resultado externo |
| --- | --- |
| Rama / commit retenidos | `lab/frappe-baseline` / `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`; checkout limpio inicial y revalidado |
| Identidad de tarea | Environment ID y hostname registrados en el JSON; primera observación 2026-10-06 02:31:11 UTC, revalidación 02:43:59–02:44:03 UTC |
| Instalación | Sitios y runtime retenidos; cero sitios nuevos, sin instalación, restore, seed ni migración manual |
| Aplicaciones | Frappe 16.36.1, ERPNext 16.36.1 y Cencomun 0.0.1 en los tres sitios; upstream limpio en los SHAs fijados |
| Servicios | Nueve servicios arrancados con los supervisores retenidos; procesos revalidados por PID/estado/start tick |
| Lectura autenticada | Reader retenido; cuatro GET HTTP 200 por adaptador y API nativa |
| Precio | P001: adaptador `50.00` y Item nativo `50.0`, equivalencia numérica |
| Stock | `WH-LAB-001-HTTP - CLAB`: adaptador `5` y Bin nativo `5.0`, equivalencia numérica |
| Readiness | Exit 0; flag LAB activo y medición de queries desactivada; producto/precio/stock coincidentes |

Los dos fallos HTTP iniciales de readiness permanecen en la evidencia. No se
registraron sus códigos HTTP ni causa, y no se les atribuye una explicación.
Una ejecución posterior pasó sin regenerar credenciales, reiniciar servicios
ni modificar configuración. El segundo shell terminó con exit 0 por ejecutar
después `services.py status`; el readiness fallido seguía teniendo exit 1.

Este PASS abarca la restauración del snapshot y las lecturas autenticadas
descritas. No acredita suites oficiales, Core Test completo, regresión de
patch ni comportamiento de esta instancia. No altera sus estados ni el
criterio 13, que permanece BLOCKED con seis escenarios UNRUN.

Límites: no se aportó identidad del ejecutor original para comparar directamente
hostname/boot ID; los hashes individuales del manifiesto y `versions.lock` no
se midieron explícitamente en este JSON; no se utilizó el verificador nuevo del
checkpoint. El commit limpio y los SHAs observados sí están registrados. No
se atribuyen al registro comprobaciones adicionales. Para repetir en el futuro,
seguir [el procedimiento](../docs/FRAPPE_CLOUD_RESTORE_CHECK.md), conservando las
identidades distintas del snapshot y del commit de preparación.
