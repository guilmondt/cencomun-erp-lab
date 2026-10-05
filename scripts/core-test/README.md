# Core Test de Frappe — LAB-ONLY-v1

Autorizado en `lab/frappe-baseline`; ninguna regla sintética es política de
producción. Plan completo: `tasks/100-ccm-core-test.md`. Oráculo y entradas
comunes para Axelor: `fixtures/ccm-core-v1/manifest.json`, con SHA256 por archivo.
Git conserva los CSV byte por byte, incluidos sus finales de registro CRLF;
no normalizarlos antes de verificar el manifiesto ni importar el mismo archivo.
Las evidencias distinguen PASS, FAIL, BLOCKED y UNRUN. El criterio 13 exige un
patch oficial posterior compatible y regresión completa; los tests previos al
patch no lo aprueban.

## Primera ejecución

1. Trabajar en `/workspace/cencomun-erp-lab`, rama `lab/frappe-baseline`.
   Leer AGENTS y el ExecPlan aprobado. No cambiar main, Axelor ni upstream.
2. Preparar las versiones fijadas, si falta el runtime:
   ```bash
   cd /workspace/cencomun-erp-lab
   bash scripts/frappe-integral/install.sh
   source scripts/frappe-integral/env.sh
   python scripts/frappe-integral/services.py start
   ```
3. Ejecutar el runner completo:
   ```bash
   bash scripts/core-test/run.sh
   ```
   Requiere Debian 13 amd64 y el runtime integral documentado. No usa root,
   Docker, secretos de producción ni datos reales. Descarga únicamente paquetes
   fijados mediante los repositorios existentes. El cliente `mariadb-dump`
   11.8.6 se extrae en un prefijo separado y se verifica por SHA256.
4. Revisar `reports/frappe-core-test.md` y
   `reports/evidence/frappe-core/summary.json`. Comandos/códigos de salida:
   `commands.json`; observaciones detalladas: `business.json`, `finance.json`,
   `http.json`, `recovery.json`, `audit.json`, `reproducibility.json` y
   `benchmark-raw.csv`. Una salida 0 del script no implica que todos los casos
   hayan pasado: revisar las matrices de casos y criterios.

El runner crea `ccm-core.test` (`ccm_core_lab`) y copia de reproducción
`ccm-core-recovery.test` (`ccm_core_recovery`). Antes de cada repetición respalda
el estado actual y restaura **solo** el laboratorio marcado desde su checkpoint
inicial verificado; nunca restaura ni elimina `ccm-frappe.test`. Conserva las
credenciales y dumps privados bajo `/workspace/.local/frappe-integral`, fuera de
Git. Los IDs técnicos nuevos se normalizan por los mappings; dinero, permisos,
stock, estados y datos funcionales conservan exactamente el oráculo.

No ejecutar una etapa sobre otra con datos acumulados: empezar con el runner o
restaurar el checkpoint antes de repetir suites completas. Para diagnosticar
un caso aislado pueden seleccionarse grupos HTTP con `CCM_HTTP_CASES`,
conservando la evidencia anterior; los casos de primera creación/concurrencia
requieren objetos nuevos o el checkpoint. Un replay no reemplaza una medición
de primera creación.

## Continuar un runtime conservado sin reiniciar los datos

```bash
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
python scripts/frappe-integral/services.py start
python scripts/core-test/http_services.py start
python scripts/frappe-integral/services.py status
"$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/readiness.py
```

El adaptador usa `127.0.0.1:8090`, consumidor ficticio `127.0.0.1:8091` y Frappe
`127.0.0.1:8000` con `Host: ccm-core.test`. El proxy baseline 8080 tiene su sitio
fijado a `ccm-frappe.test`; no se modifica. Autenticación token: archivo privado
`core-private.json`, nunca valores en instrucciones, informes ni comandos de
chat. MCP stdio ejecuta `mcp.py`, recibe su token por `CCM_MCP_AUTH` en el proceso
privado del harness y ofrece exactamente las seis operaciones del adaptador.
MCP necesita lectura del catálogo Account para validar borradores nativos;
no obtiene escritura financiera, aprobación, stock físico ni lectura de GL.

El sitio tiene `ccm_lab_enabled=1`, empresa `CCM-LAB-001`, cuentas y Bank Account
configurados por `seed.py`; los DocTypes/campos/roles/permisos/Workflow/search
se sincronizan por `bench migrate` y `core.setup.install`. El flag de medición
`ccm_measure_queries` se desactiva al terminar. El simulador Cashea se identifica
separadamente del operador físico. No hay consumidores ni mensajes externos.

## Qué se ejecuta

1. Preflight, pins, servicios y cliente de backup fijado.
2. Backup/restore del sitio marcado; migración; catálogos y fixtures nativos.
3. CO00/CO01 y TAX01-S/TAX01-W: Document APIs de ERPNext, Stock/GL Ledger,
   ventas, entregas, facturas y pagos con retenciones nativas.
4. Producto/garantía, rechazos, estados, stock insuficiente, FX por fecha y
   redondeo por línea; compras/Workflow/umbrales/autorizaciones; caja; CSV/banco.
5. Seis rutas HTTP, errores 401/403/422/409, permisos por rol/empresa, acciones
   nativas directas, MCP stdio y equivalencia de datos; caja inmutable por HTTP.
6. Creaciones/entregas/liquidaciones/importación simultáneas; pérdida de respuesta
   **tras commit** por salida 73 del adaptador; reinicio suave de MariaDB, Redis,
   web y worker; recuperación del replay. Native ledger counts prueban que no se
   duplica factura, salida, retención ni pasivo de impuesto.
7. Outbox durable; consumidor SQLite local (no DB del ERP); fallo 503, reinicio,
   reintento y reentrega. Dos entregas conservan un efecto por event_id.
8. Auditoría/immutabilidad/configuración; lectura y exportación de fixtures.
9. Otro sitio restaurado repite las 14 agrupaciones nativas de negocio/finanzas.
   Se cuentan 4 tests oficiales de utilidad **unit**, no suite completa upstream.
10. Benchmark separado: 1000 productos, 100 clientes, 1000 NEW y 1000 filas;
    20 warmups + 1000 muestras seriales para búsqueda, stock y creación NEW.
    Datos de negocio fijos, IDs deterministas por muestra. Native recorder recoge
    consultas/tiempos DB dentro del RPC sin persistir SQL/headers. Sin SLA real.
11. Registro/paquete, guardrails/diff, consulta de tags exacta y publicación.

## Problemas y pasos de resolución

### No conecta o responde 401

1. Consultar `services.py status`; arrancar los procesos que falten con `start`.
2. Verificar el sitio/puerto: Core usa 8000 + Host ccm-core.test, no el proxy 8080.
3. Si se restauró la DB, ejecutar `seed.py` mediante `site_command.py`; regenera
   claves sintéticas si difieren. Nunca imprimirlas. Cada sitio de recuperación
   tiene su propio archivo privado; no sobrescribe credenciales del sitio medido.
4. Reiniciar web/worker y adaptador; repetir las pruebas HTTP/MCP.

### Backup/restore no funciona

1. Ejecutar `python scripts/core-test/install_tools.py` con env.sh activado.
2. Añadir `core-tools/usr/bin` al PATH; comprobar `mariadb-dump --version` (11.8.6).
3. Leer solo el log saneado con
   `python scripts/core-test/log_tail.py <ruta_privada_del_log>`.
4. Verificar marca del sitio, nombre de DB, checksum del checkpoint y rutas.
   No forzar sobre un sitio no marcado. Respaldar el estado actual antes de
   restaurar. Si el runtime tiene datos y perdió su checkpoint, conservar su
   backup, crear una copia vacía aislada con los mismos pins y obtener allí un
   nuevo checkpoint; no declarar vacío un dump de datos acumulados.
5. Migrar y sembrar por APIs; repetir suites y comparar las cifras nativas.

### Faltan Currency VES, grupos hoja, cuentas o listas de precios

1. Migrar Cencomun para sincronizar campos/roles/configuración versionados.
2. Ejecutar `seed.py` con `site_command.py` y el intérprete Bench, no Python del SO.
3. Inspeccionar `core-seed.log` saneado: todos los defaults deben ser válidos.
4. Restaurar el checkpoint y repetir el caso; no deshabilitar validaciones ni
   insertar SQL de negocio. La empresa, monedas, grupos y cuentas son ficticios.

### Permisos nuevos no se aplican

1. Ejecutar `bench --site ccm-core.test clear-cache` dentro del directorio Bench.
2. Reiniciar web/worker para recargar módulos Python y hooks.
3. Repetir PERM-API-NATIVE, con llamadas directas y actor sin scope de empresa.
4. Confirmar 403/[] sin cambios; no otorgar aprobaciones al MCP para hacer pasar
   el caso. Los factories nativos pueden crear drafts, pero hooks de servidor
   exigen el servicio autorizado para las escrituras físicas/financieras.

### Dinero o contabilidad difieren

1. Conservar primer resultado/ledger y código, nunca cambiar el oráculo.
2. Identificar documento y verificar `grand_total`, `net_total`, impuestos,
   referencias de pagos, Stock Ledger y GL Entry.
3. Para retención en la misma moneda, paid_amount del Payment Entry es el **neto**,
   la referencia aplicada es el **financiado**, y deductions contienen gastos:
   ERPNext iguala received_amount a paid_amount. No tratar gasto como costo SKU.
4. En FX, construir el Payment Entry nativo con tasa de la fecha exacta y montos
   redondeados por línea; no depender de la búsqueda nativa de una tasa inversa
   del día actual. La autorización manual se conserva en un documento auditado.
5. Respaldar/restaurar y repetir CO00/CO01/TAX01 y los casos afectados.

### Tests oficiales o patch bloqueados

1. Instalar dependencias de test desde `core-test-dependencies.lock`, con env.sh.
2. No usar `--skip-test-records`: en esta versión sale 0 sin ejecutar pruebas.
3. La suite de integración tiene bootstrap lazy y puede colisionar con Standard
   Buying existente; `--skip-before-tests` no elimina ese bootstrap. Para suite
   completa usar un sitio vacío separado y preparar fixtures oficiales primero,
   o versionar nombres de listas LAB diferentes, conservando el mismo oráculo.
4. Registrar conteo real, errores y alcance. La categoría unit de utilidades es
   una comprobación separada; no representa una regresión completa post-patch.
5. Consultar tags oficiales de la misma major/minor fijada. Si no existe patch
   posterior compatible, dejar criterio 13 BLOCKED y dependientes UNRUN.
6. Cuando ambos Core Test estén estables, congelar tag/SHA/dependencias; respaldar
   y ensayar update/migrate/regresión completa/recovery en copia, sin mover pins
   del baseline. Solo entonces evaluar ese criterio.

## Comparación posterior con Axelor

Copiar el manifiesto exacto y comprobar todos sus SHA256. Mantener las mismas
entradas de productos/pedidos/compras/caja/FX/banco/roles y los mismos resultados
en `oracle.json`, TAX01 incluido. Usar las seis rutas y el contrato LAB del plan;
normalizar solamente IDs técnicos, sufijos de cuenta/almacén y timestamps
creados. CBANK aísla los cobros bancarios no aplicados de C002. Los almacenes
por escenario aíslan stock y la carga inicial se excluye de GL de ventas.
No ajustar dinero, efectos, errores o reglas para ocultar diferencias. Conservar
mismas muestras/seed/IDs, observar recursos iguales cuando disponibles y registrar
cualquier diferencia; todavía no se afirma paridad ni ganador.
