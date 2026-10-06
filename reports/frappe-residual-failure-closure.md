# Cierre residual Frappe desde 678c5ef

**Cerrado con FAIL históricos, límites demostrados y un API-key UNKNOWN.**
La conciliación inicial fue 36 PASS acotados, 1 FAIL y 19 sin resultado posterior.
Ahora los 56 IDs originales tienen 45 PASS acotados, 4 FAIL posteriores y 7
UNRUN posteriores. UNRUN significa que no se volvió a ejecutar ese método:
conserva su FAIL/ERROR original; un diagnóstico de lectura o subcaso no lo aprueba.
Los dos Client adicionales conservan ERROR y no se reejecutaron en este cierre.

Los completos permanecen **Frappe FAIL: 2.326 ejecutadas, 2.220 PASS/9 FAIL/
47 ERROR/50 SKIP; ERPNext FAIL: 3.255 ejecutadas, 3.251 PASS/4 ERROR/0 SKIP**.
No se suman PASS acotados, no se recalculan completos ni se repitieron suites.
La matriz reproducible está en [residual-final-matrix.json](evidence/frappe-official/residual-final-matrix.json).

Core conserva su resultado anterior: **34 grupos PASS, 13 criterios PASS y
C13 BLOCKED**, seis escenarios PATCH UNRUN. No es una nueva regresión Core.

## Intentos de este cierre

Acceso confirmado a HEAD 678c5ef limpio, cero runners y 97 logs retenidos antes
de continuar. El coordinador ya publicó ese snapshot; no se repitieron publicación
ni restauración externa fcf690d. Sitio nuevo oficial `ccm-upstream-frappe-residual.test`,
con preparación nativa CI y credencial común retenida; se conservaron todos los anteriores.
Fuentes/pins/oráculo permanecen fijados. No hubo consultas externas ni ampliación de red.

**15 ejecuciones nativas seleccionadas: 11 PASS/4 FAIL/0 ERROR/0 SKIP**, en diez
intentos. Son métodos seleccionados, no módulos completos. Un intento tiene cero
pruebas porque falló readiness antes de iniciar el runner; no hubo bootstrap nativo
ni resultado del método en ese intento. Hay además un subcaso nativo de esquema
FAIL, separado del contador de pruebas. Los métodos cargados pero no seleccionados
quedan fuera del alcance; los IDs seleccionados sin resultado se indican en el JSON.

| Resultado nativo | Métodos seleccionados | Ejecutadas | PASS | FAIL | ERROR | SKIP |
|---|---|---:|---:|---:|---:|---:|
| [frappe-test_activity_log-selected-attempt-1.json](evidence/frappe-official/frappe-test_activity_log-selected-attempt-1.json) | test_activity_log, test_brute_security | 2 | 2 | 0 | 0 | 0 |
| [frappe-test_commands-selected-attempt-1.json](evidence/frappe-official/frappe-test_commands-selected-attempt-1.json) | test_backup_with_custom_path, test_backup_with_different_file_paths | 2 | 0 | 2 | 0 | 0 |
| [frappe-test_commands-selected-attempt-2.json](evidence/frappe-official/frappe-test_commands-selected-attempt-2.json) | test_rq_pool_idle_cpu_usage | 1 | 1 | 0 | 0 | 0 |
| [frappe-test_db-selected-attempt-1.json](evidence/frappe-official/frappe-test_db-selected-attempt-1.json) | test_connect_fails_with_wrong_credentials_by_env | 1 | 0 | 1 | 0 | 0 |
| [frappe-test_db-selected-attempt-2.json](evidence/frappe-official/frappe-test_db-selected-attempt-2.json) | test_connect_fails_with_wrong_credentials_by_env | 0 | 0 | 0 | 0 | 0 |
| [frappe-test_email-selected-attempt-1.json](evidence/frappe-official/frappe-test_email-selected-attempt-1.json) | test_send_email, test_store_attachments | 2 | 2 | 0 | 0 | 0 |
| [frappe-test_email-selected-attempt-2.json](evidence/frappe-official/frappe-test_email-selected-attempt-2.json) | test_send_email, test_store_attachments | 2 | 2 | 0 | 0 | 0 |
| [frappe-test_email_account-selected-attempt-1.json](evidence/frappe-official/frappe-test_email_account-selected-attempt-1.json) | test_threading_by_subject, test_threading_by_message_id, test_unread_notification | 3 | 3 | 0 | 0 | 0 |
| [frappe-test_rq_job-selected-attempt-1.json](evidence/frappe-official/frappe-test_rq_job-selected-attempt-1.json) | test_memory_usage | 1 | 0 | 1 | 0 | 0 |
| [frappe-test_rq_job-selected-attempt-2.json](evidence/frappe-official/frappe-test_rq_job-selected-attempt-2.json) | test_memory_usage | 1 | 1 | 0 | 0 | 0 |

El segundo EmailIntegration confirma ambos casos después de corregir el import
anticipado del guard. RQ memoria conserva el intento FAIL previo y el PASS posterior.
Para CPU/memoria no se activó profiling de frames; el guard offline sí permaneció activo.

## Primera causa y límite de cada línea residual

- **EmailIntegration (2 PASS):** los originales fallaron en setUp al borrar mensajes
  SMTP4dev, rechazados por Responses antes del socket. El guard corregido respeta
  mocks nativos sin passthrough; preparación/SMTP4dev locales y procesos limpios
  pasan envío/adjuntos, también después de diferir imports. No se atribuye al servidor
  caído el rechazo histórico por mock.
- **ActivityLog (2 PASS):** la primera operación fallida fue LoginManager, credenciales
  inválidas. El test de comandos anterior llegó a cambiar la contraseña a su segundo
  valor ficticio y falló al restaurarla: Click leyó el prefijo de la credencial retenida
  como opción. Lectura privada del hash retenido coincide con ese segundo valor y
  no con conf/común. También se conserva el defecto anterior de precedencia del helper.
  Sitio nuevo alineado con preparación nativa pasa ambos casos; no se reparó ni se
  restableció la contraseña del antiguo.
- **DBUpdateSanity:** primera aserción exige cero ALTER; obtuvo DROP/ADD del mismo
  `unique_dedup_key` en Automation Trigger Queue. Columna generada ausente de meta;
  sincronización elimina el índice y on_doctype_update lo recrea. Se verificó únicamente
  ese subcaso con `assertQueryCount(0)`: FAIL, dos ALTER exactos. El posterior
  `_io.TextIOWrapper.writeln` AttributeError es manejo nativo del resultado del subtest.
  No se volvió a muestrear aleatoriamente 20 DocTypes para buscar PASS. Cambiar el
  contrato de esquema/result-stream exige upstream/pins; método posterior UNRUN.
- **EmailAccount (3 PASS):** primeros fallos originales: lista insuficiente (IndexError
  en línea278), referencia distinta en línea323 y ausencia de Email Queue en línea81.
  Los tres métodos pasan con fixtures nativos en el sitio limpio. El estado histórico
  completo de correo/precedentes no fue capturado; no se afirma qué módulo lo alteró.
  Se detiene la línea al PASS acotado; no se amplía a otros casos de correo.
- **Backups (2 FAIL):** los originales solo muestran salida1/mensaje genérico, sin
  Errno30. Nuevas reproducciones capturan el OSError30 bajo HOME en línea107 (ruta
  común) y117 (rutas por archivo) de setup_backup_directory. Se enlazan por ventanas
  before/after de cada ID y PID hijo; ambos comandos conservan FAIL. El handler nativo
  oculta la excepción salvo verbose; el observador solo registra tipo/errno/frames,
  sin dumps ni secretos. HOME no se escribe, remapea ni cambia.
- **existing_db_username (sin repetir):** importación SQL nativa devuelve1045 tras
  CREATE USER localhost sin contraseña. Cuenta retenida encontrada con cadena de
  autenticación vacía; `CREATE USER IF NOT EXISTS` no establece el password al existir.
  Conserva FAIL. No se ejecuta el caso que crea/cambia credenciales ni se modifica
  cuenta/grant/instalador para buscar PASS.
- **set_password (sin repetir):** primeros dos cambios oficiales habían pasado;
  restaura en línea471 con una credencial cuyo prefijo es interpretado como opción
  por Click, exit2. Conserva FAIL y su estado retenido; corregir argumentos del test
  nativo o cambiar la credencial excede el alcance. No reset ni reejecución.
- **RQ pool (PASS):** original CPU46 frente a máximo10 en primera medición. Proceso
  limpio, guard activo e invocación sin profiling pasa ambas aserciones nativas.
  No se midió la contribución exacta de startup/profiling en el histórico; no se
  atribuye retrospectivamente todo46 a una única causa.
- **RQ memoria (FAIL→PASS):** reproducción58 MiB frente a55,65. Defecto propio:
  sitecustomize importaba requests antes de que el worker lo necesitara. El guard
  instala ahora el mismo wrapper antes de finalizar el primer import nativo de requests;
  DNS/socket siguen protegidos desde startup, mocks sin passthrough intactos. Worker
  nuevo después de terminar el primer intento obtiene52 MiB: PASS. No se reinicia un
  consumidor durante un caso ni se cambia la aserción53×1,05.
- **DB credentials env (FAIL y arranque TCP BLOCKED):** socket propio tiene precedencia
  sobre host/puerto; primera aserción de host inválido no lanza OperationalError. Se
  reprodujo ese FAIL. Solo en sitio diagnóstico nuevo se probó None para db_socket;
  readiness no llegó al runner (cero pruebas). Sondeo nativo TCP devuelve1130; servidor
  skip_name_resolve=ON y cuenta solo localhost. Se restauró el socket original del sitio
  nuevo. Resolver TCP requiere cambiar acceso DB, fuera del alcance; no se conceden
  grants ni se inventa una excepción para que la aserción pase.

Los fallos de preparación auxiliares se conservan en residual-db-transport-after.json:
source relativo desde cwd Bench no encontró env (cero tests/cambios); `--parse null`
falló porque el parser nativo usa ast.literal_eval; `--parse None` sí fue válido.
La ruta de inicio debe cargarse desde el repositorio o mediante ruta absoluta.
El primer arranque MariaDB sin env.sh no encontró liburing.so.2; cargar el env retenido
resolvió ese arranque, sin instalar bibliotecas ni cambiar pins.

## API key pendiente: solo lectura, FAIL/UNKNOWN

[residual-api-key-read-only.json](evidence/frappe-official/residual-api-key-read-only.json)
registra que api_key y secreto cifrado existen; el key efectivo coincide con el del
sitio, pero no descifra el ciphertext. Se revisaron77 configuraciones retenidas;
ninguna lo descifra. El valor generado existe en locales privados de la traza, sin
publicarlo. Se conservaron los eventos nativos de carga de config/presencia de key
por PID; no contienen identidad del key para establecer la cronología exacta.

La precedencia y TTL60 del caché nativo son verificables en fuentes, pero no prueban
quién cambió el key/ciphertext. No se llamó generate_keys, get_encryption_key, reset,
check_password ni login en el diagnóstico; Fernet usó exclusivamente keys existentes.
Próximo paso: revisar trazas privadas ya existentes de creación/caché con identidad
continuada. Si no existen, cualquier experimento nuevo que genere credenciales debe
ser un encargo separado y aprobado sobre sitio descartable; no regenerar el retenido.
UNKNOWN no equivale a imposibilidad demostrada.

## Matriz de los 56 IDs originales

El estado original es inmutable. PASS posterior acredita solo el alcance/sitio del
archivo enlazado. UNRUN posterior conserva FAIL/ERROR original. La clasificación y
próximo paso precisos de cada fila están en residual-final-matrix.json; hashes de
cada bloque privado permiten enlazar la primera causa sin publicar el log.

| ID exacto | Original | Posterior acotado | Evidencia posterior / diagnóstico |
|---|---|---|---|
| `frappe.automation_engine.tests.test_actions.TestCallWebhook.test_internal_addresses_are_blocked` | ERROR | UNRUN | [frappe-final-failure-diagnostics-v2.json](evidence/frappe-official/frappe-final-failure-diagnostics-v2.json) |
| `frappe.core.doctype.activity_log.test_activity_log.TestActivityLog.test_activity_log` | ERROR | PASS | [frappe-test_activity_log-selected-attempt-1.json](evidence/frappe-official/frappe-test_activity_log-selected-attempt-1.json); [residual-retained-password-read-only.json](evidence/frappe-official/residual-retained-password-read-only.json) |
| `frappe.core.doctype.activity_log.test_activity_log.TestActivityLog.test_brute_security` | ERROR | PASS | [frappe-test_activity_log-selected-attempt-1.json](evidence/frappe-official/frappe-test_activity_log-selected-attempt-1.json); [residual-retained-password-read-only.json](evidence/frappe-official/residual-retained-password-read-only.json) |
| `frappe.email.test_smtp.TestSMTP.test_smtp_ssl_session` | ERROR | UNRUN | [frappe-final-failure-diagnostics-v2.json](evidence/frappe-official/frappe-final-failure-diagnostics-v2.json) |
| `frappe.email.test_smtp.TestSMTP.test_smtp_tls_session` | ERROR | UNRUN | [frappe-final-failure-diagnostics-v2.json](evidence/frappe-official/frappe-final-failure-diagnostics-v2.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_validate_doc_events` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_validate_headers` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_validate_request_body_form` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_validate_request_body_json` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_validate_request_url` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_webhook_req_log_creation` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_webhook_trigger_with_enabled_webhooks` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_webhook_with_array_body` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_webhook_with_dynamic_url_disabled` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.integrations.doctype.webhook.test_webhook.TestWebhook.test_webhook_with_dynamic_url_enabled` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_api.TestResourceAPI.test_unauthorized_call_v1` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_api_v2.TestResourceAPIV2.test_unauthorized_call_v2` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_allow_login_using_mobile` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_allow_login_using_only_email` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_allow_login_using_username` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_allow_login_using_username_and_mobile` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_correct_cookie_expiry_set` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_deny_multiple_login` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_disable_user_pass_login` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_auth.TestAuth.test_login_with_email_link` | ERROR | PASS | [frappe-sequence-test_perf-attempt-1.json](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json) |
| `frappe.tests.test_client.TestClient.test_array_values_in_request_args` | ERROR | PASS | [frappe-test_client-attempt-2.json](evidence/frappe-official/frappe-test_client-attempt-2.json) |
| `frappe.tests.test_db_update.TestDBUpdateSanityChecks.test_no_unnecessary_migrates` | ERROR | UNRUN | [residual-schema-contract-read-only.json](evidence/frappe-official/residual-schema-contract-read-only.json); [residual-schema-subcase.json](evidence/frappe-official/residual-schema-subcase.json) |
| `frappe.email.doctype.email_account.test_email_account.TestEmailAccount.test_threading_by_subject` | ERROR | PASS | [frappe-test_email_account-selected-attempt-1.json](evidence/frappe-official/frappe-test_email_account-selected-attempt-1.json) |
| `frappe.tests.test_email.TestEmailIntegrationTest.test_send_email` | ERROR | PASS | [frappe-test_email-selected-attempt-2.json](evidence/frappe-official/frappe-test_email-selected-attempt-2.json); [frappe-test_email-selected-attempt-1.json](evidence/frappe-official/frappe-test_email-selected-attempt-1.json) |
| `frappe.tests.test_email.TestEmailIntegrationTest.test_store_attachments` | ERROR | PASS | [frappe-test_email-selected-attempt-2.json](evidence/frappe-official/frappe-test_email-selected-attempt-2.json); [frappe-test_email-selected-attempt-1.json](evidence/frappe-official/frappe-test_email-selected-attempt-1.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_auth_via_api_key_secret` | ERROR | FAIL | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json); [residual-api-key-read-only.json](evidence/frappe-official/residual-api-key-read-only.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_create_doc` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_delete_doc` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_get_doc` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_get_single` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_get_value_by_filters` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_get_value_by_name` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_get_value_with_malicious_query` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_insert_many` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_list_docs` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_list_summary` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_update_child_doc` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_frappe_client.TestFrappeClient.test_update_doc` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_oauth20.TestOAuth20.test_login_using_implicit_token` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.tests.test_perf.TestPerformance.test_req_per_seconds_basic` | ERROR | PASS | [frappe-test_perf-attempt-1.json](evidence/frappe-official/frappe-test_perf-attempt-1.json) |
| `frappe.tests.test_utils.TestAppParser.test_app_name_parser` | ERROR | UNRUN | [frappe-final-failure-diagnostics-v2.json](evidence/frappe-official/frappe-final-failure-diagnostics-v2.json) |
| `frappe.workflow.doctype.workflow.test_workflow.TestWorkflow.test_sync_tasks` | ERROR | PASS | [frappe-sequence-test_oauth20-attempt-2.json](evidence/frappe-official/frappe-sequence-test_oauth20-attempt-2.json) |
| `frappe.commands.test_commands.TestBackups.test_backup_with_custom_path` | FAIL | FAIL | [frappe-test_commands-selected-attempt-1.json](evidence/frappe-official/frappe-test_commands-selected-attempt-1.json); [frappe-test_commands-selected-attempt-1-observations.json](evidence/frappe-official/frappe-test_commands-selected-attempt-1-observations.json) |
| `frappe.commands.test_commands.TestBackups.test_backup_with_different_file_paths` | FAIL | FAIL | [frappe-test_commands-selected-attempt-1.json](evidence/frappe-official/frappe-test_commands-selected-attempt-1.json); [frappe-test_commands-selected-attempt-1-observations.json](evidence/frappe-official/frappe-test_commands-selected-attempt-1-observations.json) |
| `frappe.commands.test_commands.TestCommands.test_existing_db_username` | FAIL | UNRUN | [residual-existing-db-user-read-only.json](evidence/frappe-official/residual-existing-db-user-read-only.json) |
| `frappe.commands.test_commands.TestCommands.test_set_password` | FAIL | UNRUN | [residual-retained-password-read-only.json](evidence/frappe-official/residual-retained-password-read-only.json) |
| `frappe.commands.test_commands.TestRQWorker.test_rq_pool_idle_cpu_usage` | FAIL | PASS | [frappe-test_commands-selected-attempt-2.json](evidence/frappe-official/frappe-test_commands-selected-attempt-2.json) |
| `frappe.core.doctype.rq_job.test_rq_job.TestRQJob.test_memory_usage` | FAIL | PASS | [frappe-test_rq_job-selected-attempt-2.json](evidence/frappe-official/frappe-test_rq_job-selected-attempt-2.json); [frappe-test_rq_job-selected-attempt-1.json](evidence/frappe-official/frappe-test_rq_job-selected-attempt-1.json); [residual-worker-memory-v2.json](evidence/frappe-official/residual-worker-memory-v2.json) |
| `frappe.tests.test_db.TestDbConnectWithEnvCredentials.test_connect_fails_with_wrong_credentials_by_env` | FAIL | FAIL | [frappe-test_db-selected-attempt-1.json](evidence/frappe-official/frappe-test_db-selected-attempt-1.json); [residual-db-transport-before.json](evidence/frappe-official/residual-db-transport-before.json); [residual-db-transport-after.json](evidence/frappe-official/residual-db-transport-after.json); [frappe-test_db-selected-attempt-2.json](evidence/frappe-official/frappe-test_db-selected-attempt-2.json) |
| `frappe.email.doctype.email_account.test_email_account.TestEmailAccount.test_threading_by_message_id` | FAIL | PASS | [frappe-test_email_account-selected-attempt-1.json](evidence/frappe-official/frappe-test_email_account-selected-attempt-1.json) |
| `frappe.email.doctype.email_account.test_email_account.TestEmailAccount.test_unread_notification` | FAIL | PASS | [frappe-test_email_account-selected-attempt-1.json](evidence/frappe-official/frappe-test_email_account-selected-attempt-1.json) |

## Dos Client adicionales, fuera de los 56

| ID exacto | Resultado conservado | Causa / evidencia | Nueva ejecución aquí |
|---|---|---|---|
| `frappe.tests.test_client.TestClient.test_http_valid_method_access` | ERROR | request presente, cache_control=None, atributo no_cache en website/utils.py:537; [auth-bounded-results.json](evidence/frappe-official/auth-bounded-results.json) | No |
| `frappe.tests.test_client.TestClient.test_set_value` | ERROR | request presente, cache_control=None, atributo no_cache en website/utils.py:537; [auth-bounded-results.json](evidence/frappe-official/auth-bounded-results.json) | No |

No se persigue ni se añade request ficticio, se borra Workflow o se cambia su fixture.

## ERPNext FX y C13, separados

| ID exacto | Estado conservado | Causa demostrada |
|---|---|---|
| `erpnext.accounts.doctype.exchange_rate_revaluation.test_exchange_rate_revaluation.TestExchangeRateRevaluation.test_05_revaluation_journal_reversal` | ERROR | Sin fila elegible en ventana histórica; resolver devuelve0 y JE usa fallback1; débito USD cambia0→100 INR mientras pérdida8000 permanece, total8100/8000. [revaluation-cause](evidence/frappe-official/erpnext-revaluation-cause.json) |
| `erpnext.selling.doctype.quotation.test_quotation.TestQuotation.test_make_quotation_qar_to_inr` | ERROR | Sin fila oficial elegible para par/fecha/for_selling, resolver0 después de rechazo offline ligado al mismo PID. [diagnóstico](evidence/frappe-official/erpnext-final-failure-diagnostics-v2.json) |
| `erpnext.stock.doctype.serial_no.test_serial_no.TestSerialNo.test_inter_company_transfer_fallback_on_cancel` | ERROR | Sin fila oficial elegible para par/fecha/for_selling, resolver0 después de rechazo offline ligado al mismo PID. [diagnóstico](evidence/frappe-official/erpnext-final-failure-diagnostics-v2.json) |
| `erpnext.stock.doctype.serial_no.test_serial_no.TestSerialNo.test_inter_company_transfer_intermediate_cancellation` | ERROR | Sin fila oficial elegible para par/fecha/for_selling, resolver0 después de rechazo offline ligado al mismo PID. [diagnóstico](evidence/frappe-official/erpnext-final-failure-diagnostics-v2.json) |

No se repitió ERPNext, inventaron tasas ni cambiaron los seis fixtures oficiales.
C13 permanece **BLOCKED, seis PATCH UNRUN**: no existe patch compatible posterior
16.36 en la comprobación oficial retenida; no se ensayó minor ni se modificaron pins.
[patch.json](evidence/frappe-core/patch.json) mantiene comandos y SHAs originales.

## Conservación, comprobación Cencomun e inicio

Preservación: 10.040 artefactos comprobados, 10.038 idénticos y dos logs de servicios
solo ampliados conservando el prefijo; 45 configuraciones privadas idénticas y16 sitios
oficiales legibles. No se publican raw logs/XML, credenciales, dumps ni configuraciones
privadas. Los complete FAIL, interrupciones, SKIP, intentos previos y subcasos permanecen.

Integridad original: 49.823 archivos, mismo manifest antes/después. Fuentes originales
Frappe/ERPNext limpias y pins/17 archivos compartidos/recibo cloud idénticos.
Lectura Reader autenticada de P001 **USD50.00/stock5**, adaptador y API nativa iguales;
mutaciones0, LAB activo y métricas0. Core no se repitió porque el runtime original no
cambió. Alcance conservado de34 grupos PASS. [cierre](evidence/frappe-official/residual-closure.json)
y [integridad](evidence/frappe-official/cencomun-residual-integrity-after.json).

## Procedimiento reproducible y decisiones necesarias

1. Leer tasks/105, AGENTS y versions.lock; verificar HEAD/ref y cero runners con
   `active_runners()` del harness. Conservar manifests antes de preparar o arrancar.
   No ejecutar ninguna suite completa ni los casos que cambian passwords/API keys.
2. En cwd del repositorio, cargar `source scripts/frappe-integral/env.sh`, añadir
   official-tools/bin y core-tools/usr/bin al PATH, exportar CCM_OFFICIAL_OFFLINE=1
   y PYTHONPATH al observer. HOME/red/oráculo y configs comunes permanecen intactos.
3. Un sitio nuevo requiere `prepare.py frappe --residual` una sola vez; el slot
   retenido rechaza re-preparación. Nunca borrar el slot anterior ni forzar instalación.
   El código preparado desde este cierre conserva socket porque TCP exige acceso nuevo.
4. `run.py frappe --site ccm-upstream-frappe-residual.test --module MODULO --test METODO
   --offline --auth-diagnostics` ejecuta solo el método elegido y reserva siguiente
   intento. Añadir --observe y CCM_OFFICIAL_RESIDUAL_DIAG=1 para causa backup/email;
   para CPU/memoria omitir --observe. SMTP4dev y worker se arrancan solo si ese caso
   los requiere, con sus gestores exclusivos y guard activo. Los comandos exactos de
   cada intento, site/SHA/contador y selección se conservan en sus JSON enlazados.
5. Publicar derivados una sola vez después de finalizar. `residual_schema.py` comprueba
   exclusivamente el DocType original con la aserción nativa; no es todo el método
   aleatorio. Los scripts de evidencia/preservación usan creación exclusiva: no borrar
   salidas para sobrescribirlas; una revisión debe tener otro nombre/versionado.
6. Ante HOME30, conservar FAIL y detener. Ante1130 TCP, conservar arranque BLOCKED,
   no cambiar grants. Ante restauración de password/parser o cuenta sin password,
   conservar FAIL; no repetir esos tests ni cambiar credenciales. Ante API-key, solo
   lectura y próximo paso descrito arriba. No queda una pregunta de negocio pendiente.
7. El coordinador revisará el nuevo ref exacto y las instrucciones ordinarias de
   docs/FRAPPE_ENVIRONMENT_START.md. Repositorio/ref/start_skill son los únicos campos
   propuestos; red/dominios/install_script/secretos/variables/privacidad/permisos intactos.
   Guardar/Publicar queda pendiente exclusivamente del coordinador; no se repite aquí.

Validaciones separadas: 55 controles del harness PASS, cinco del paquete fuente y
cinco de wheel PASS, build/verify-repo/diff-check PASS. No sustituyen oficiales.
El saneamiento cotejó 97 valores privados retenidos contra archivos nuevos/cambiados,
sin coincidencias. Cuatro fixtures públicos se excluyeron solo por igualdad exacta
con el blob Payments fijado; no se ocultó ni alteró ningún ID de la matriz.

PR #4 permanece borrador; código y evidencia saneada se publican solo en lab/frappe-baseline.
