# Recuperación de evidencia tras perder acceso al ejecutor

Estado comprobado el 2026-10-06, después de recuperar acceso a esta misma tarea.
No se ha iniciado otra suite ni se han reiniciado servicios durante esta
recuperación. La comprobación de `fcf690d` en una tarea cloud nueva, iniciada por
el coordinador, terminó según su confirmación posterior. Es independiente;
su resultado y evidencia siguen pendientes de recepción, sin volver a ejecutarla.

## Error exacto y alcance

La lectura de una sesión de ejecución devolvió:

```text
write_stdin failed: Unified exec process failed:
exec-server transport disconnected; failed to resume exec-server session:
recovery timed out after 25s
```

Una edición de preparación también falló con:

```text
apply_patch verification failed: Failed to read file to update /workspace/cencomun-erp-lab/scripts/official-tests/isolate_bench.py: exec-server transport closed
```

Es un fallo de transporte con el ejecutor. No se observó una denegación de
permisos ni de revisión automática. La causa de la desconexión y la terminación
de los procesos no está demostrada; no se atribuye a memoria, a ERPNext ni a la
tarea cloud separada. Los contadores actuales de memoria no reconstruyen el
estado del ejecutor antes de la desconexión.

## Qué se recuperó y qué no se puede afirmar

| Elemento | Observación verificable |
| --- | --- |
| Rama y commit | `lab/frappe-baseline`, `fcf690dbc58b2b2dcf8d045c49976e3613e804cf` |
| Cambios locales | 31 archivos modificados o nuevos preservados; no tienen commit ni push de esta fase |
| ERPNext, intento 2 | No existe ahora un proceso del driver o del runner; tampoco resultado JSON final |
| Log ERPNext | Recuperable: 2682 bytes; última escritura `2026-10-06T02:22:21.859420+00:00` |
| XML ERPNext | Existe, pero tiene cero bytes; no contiene evidencia por test |
| Conteo ERPNext comprobado | Categoría unit: `Ran 2 tests in 0.011s`, `OK` |
| Categoría ERPNext incompleta | El runner anunció 3253 pruebas de categoría unspecified; no existe su resumen final. La cantidad efectivamente ejecutada y los resultados individuales son desconocidos |
| Estado de suite ERPNext | **BLOCKED por interrupción / resultado incompleto**. Las dos unitarias no representan la suite completa; puntos, E y F del progreso no se convierten en conteos ni resultados individuales |
| Frappe, intento completo 2 | **FAIL**, 2275 pruebas según los resúmenes nativos; 2279 eventos JUnit: PASS 2006, FAIL 10, ERROR 212, SKIP 51. Los eventos adicionales no son pruebas adicionales |
| Regresión oficial RQ | 13 pruebas PASS en el intento 3 del módulo; no reemplazan la suite Frappe completa |
| ERPNext, intento 1 | Evidencia previamente puesta en cuarentena por colisión de nombres; conteos no válidos. Se conserva y no se suma |
| Servicios actuales | MariaDB, ambos Redis, web, Socket.IO, worker, Nginx, worker oficial y SMTP4dev detenidos |
| Datos MariaDB | Directorio `mariadb-data` retenido, aproximadamente 1.2 GiB, copiado con el servidor detenido. Su restauración todavía no fue probada |
| Core Test | Resultados históricos de `fcf690d`; regresión posterior a esta preparación todavía pendiente |
| Criterio 13 | Continúa **BLOCKED** y sus seis escenarios **UNRUN**; esta recuperación no cambia los pins ni acredita un patch |

El comando del intento ERPNext interrumpido fue:

```text
bench --site ccm-upstream-erpnext.test run-tests --app erpnext --junit-xml-output /workspace/.local/frappe-integral/official-tests/erpnext-full-attempt-2.xml
```

Se ejecutaba en `/workspace/.local/frappe-integral/official-bench`, con servidor
propio en el puerto 8005. No se ejecutó de nuevo para intentar recuperar logs.

## Copias privadas conservadas

Directorio con permisos 0700, archivos con permisos 0600:

```text
/workspace/.local/frappe-integral/recovery/executor-20261006T023334Z/
```

| Archivo | Contenido | SHA-256 |
| --- | --- | --- |
| `local-evidence.tar.gz` | 31 archivos del repositorio, logs/XML y estados privados de pruebas oficiales, configuraciones de sitios; 493376 bytes | `09103dda624810f741dea6527fb54e715f68cf55f1939f58582f20f23bc706f8` |
| `runtime-retained.tar.gz` | Archivos retenidos de MariaDB, logs de runtime, estado/configuración y datos del consumidor; 113528757 bytes | `b1b262c2de2be93a9b8be6ff3b08b293ca65a1571e3a05a0f272eb227207c609` |

Un checkpoint privado posterior, `worktree-current.tar.gz`, conservó 34 archivos
incluidas las observaciones de recuperación. Los tres archivos se verificaron
por SHA256 y lectura completa; los hashes están en el manifiesto privado.

`worktree.patch`, `git-status.txt` y `manifest.json` permiten reconstruir y
verificar los cambios. Se verificó lectura del archivo de evidencia y su hash.
La copia de archivos MariaDB es conservación tras interrupción, no un backup
lógico validado. Los archivos privados contienen credenciales ficticias y no
deben agregarse a Git ni adjuntarse como evidencia pública sin redacción.

## Pasos para continuar sin perder evidencia ni duplicar ejecuciones

1. Continuar en esta misma tarea y rama. Comprobar `git status --short --branch`
   y `git rev-parse HEAD`; conservar los cambios presentes. No sustituir este
   workspace por el snapshot guardado ni ejecutar reset, limpieza o creación
   de sitios para resolver la desconexión.
2. Verificar las copias privadas con `sha256sum` sobre los dos archivos y
   cotejar la tabla anterior; consultar `manifest.json`. Mantener originales
   y copias, sin extraerlos encima de los archivos de trabajo.
3. Comprobar nuevamente procesos y `python scripts/frappe-integral/services.py
   status` antes de cualquier arranque. Si existe un runner activo, observar
   ese runner; no lanzar otro. Un PID antiguo en un archivo de estado no prueba
   que siga vivo: comprobar identidad y tiempo de inicio del proceso.
4. La ejecución ERPNext interrumpida queda documentada con conteo total
   desconocido y sin resultados individuales. Si después se decide repetir,
   usar una reserva nueva de intento del harness y archivos nuevos; nunca
   sobrescribir `erpnext-full-attempt-2.*`. Cargar únicamente los servicios y
   la preparación autorizados, manteniendo versiones y fixtures oficiales.
5. Antes de publicar resultados, redactar credenciales de los registros
   conservados, distinguir resúmenes nativos de eventos JUnit y repetir la
   regresión Cencomun afectada por preparación. No mantener PASS nuevo sin
   cobertura ni convertir la interrupción en éxito de suite.
6. Recibir por separado la evidencia de la tarea cloud nueva: identidad de
   tarea, commit, servicios y precio/stock autenticados. Otro sitio local o
   esta copia privada no acredita restauración cloud. No repetir
   Guardar/Publicar del entorno.

Este informe documenta la recuperación; no certifica la finalización de las
suites ni la restauración de MariaDB. PR #4 conserva su condición de borrador;
en esta recuperación no se cambiaron remotos, producción, main ni Axelor.
