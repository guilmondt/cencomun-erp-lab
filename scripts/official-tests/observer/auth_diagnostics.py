"""Read-only, opt-in auth/context evidence. No credential/hash/token values.

Native authentication may itself update login trackers; these observers do not.
Only passlib verification of a read-only native QB result is used for comparison.
"""
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

RETAINED = Path('/workspace/.local/frappe-integral/official-tests/frappe-cause-fixed-private.json')
REASONS = {'Invalid login credentials', 'Incomplete login details',
           'User disabled or missing', 'Incorrect password', 'Logged In', 'No App',
           'Password Reset', 'Login with username and password is not allowed.'}


def retained_password():
    return json.loads(RETAINED.read_text())['admin_password']


def matches_retained(value):
    return bool(value is not None and value == retained_password())


def credential_state(f):
    from frappe.utils.password import passlibctx
    auth = f.qb.DocType('__Auth')
    rows = (f.qb.from_(auth).select(auth.password)
            .where((auth.doctype == 'User') & (auth.name == 'Administrator') &
                   (auth.fieldname == 'password') & (auth.encrypted == 0))).run()
    conf = f.conf.get('admin_password')
    stored = rows[0][0] if rows else None
    common = json.loads(Path(f.local.sites_path, 'common_site_config.json').read_text()).get('admin_password')
    return {'config_admin_password_present': bool(conf),
            'config_matches_retained': matches_retained(conf),
            'administrator_auth_record_present': bool(stored),
            'retained_matches_native_hash': bool(stored and passlibctx.verify(retained_password(), stored)),
            'config_matches_native_hash': bool(stored and conf and passlibctx.verify(conf, stored)),
            'common_admin_password_present': bool(common),
            'common_matches_native_hash': bool(stored and common and passlibctx.verify(common, stored)),
            'config_matches_common': bool(conf and common and conf == common)}


def context(f):
    request = getattr(f.local, 'request', None)
    control = getattr(request, 'cache_control', None)
    return {'request_is_none': request is None,
            'request_type': type(request).__module__ + '.' + type(request).__name__,
            'request_truthy': bool(request),
            'cache_control_is_none': control is None,
            'cache_control_has_no_cache': hasattr(control, 'no_cache')}


def frames(frame):
    result = []
    while frame and len(result) < 30:
        result.append({'file': frame.f_code.co_filename, 'line': frame.f_lineno,
                       'function': frame.f_code.co_name})
        frame = frame.f_back
    return result


def redirect(url):
    p = urlsplit(str(url))
    return {'route': p.path, 'query_parameter_names': sorted(parse_qs(p.query, keep_blank_values=True)),
            'fragment_parameter_names': sorted(parse_qs(p.fragment, keep_blank_values=True))}


def response_data(response):
    data = {'effective_route': urlsplit(response.url).path,
            'redirect_history': [{'status': r.status_code, 'route': urlsplit(r.url).path,
                                  'location': redirect(r.headers.get('Location', ''))}
                                 for r in response.history],
            'location': redirect(response.headers.get('Location', ''))}
    try:
        body = response.json()
    except (ValueError, AttributeError):
        body = {}
    if isinstance(body, dict):
        kind = body.get('exc_type')
        # No raw exception strings, response bodies, cookies or headers.
        data['native_exception_type'] = kind if isinstance(kind, str) and kind.isidentifier() else None
        reason = body.get('message')
        data['native_reason'] = reason if isinstance(reason, str) and reason in REASONS else None
        data['native_message_present'] = 'message' in body
    return data


def snapshot(f, emit, stage):
    emit('auth_state', stage=stage, site=f.local.site, **context(f), **credential_state(f),
         auth_settings={k: f.db.get_single_value('System Settings', k) for k in (
             'disable_user_pass_login', 'allow_consecutive_login_attempts',
             'allow_login_after_fail', 'enable_two_factor_auth', 'force_user_to_reset_password')},
         active_todo_workflows=f.get_all('Workflow', filters={'document_type': 'ToDo', 'is_active': 1},
                                       fields=['name', 'is_active', 'send_email_alert']),
         cached_todo_workflow=f.cache.hget('workflow', 'ToDo'))


def profile(frame, event, arg, emit):
    if event not in ('call', 'return'):
        return
    name, path = frame.f_code.co_name, frame.f_code.co_filename
    f = sys.modules.get('frappe')
    if f is None:
        return
    if path.endswith('frappe/parallel_test_runner.py') and name == 'run_tests_for_file' and event == 'return':
        if f.db:
            snapshot(f, emit, 'native_module_return')
    elif (path.endswith('werkzeug/local.py') or path.endswith('frappe/utils/local.py')) and name in (
            '__setattr__', '__delattr__', '__release_local__', 'release_local'):
        if name in ('__release_local__', 'release_local') or frame.f_locals.get('name') == 'request':
            emit('request_context_transition', operation=name + '_' + event,
                 caller=frames(frame.f_back)[:8], **context(f))
    elif path.endswith('frappe/__init__.py') and name in ('init', 'destroy'):
        emit('request_context_transition', operation=name + '_' + event,
             caller=frames(frame.f_back)[:8], **context(f))
    elif event == 'return' and path.endswith('frappe/config.py') and name in ('get_site_config', 'get_conf'):
        emit('auth_config_loaded', function=name, site=frame.f_locals.get('site'),
             native_site_current=getattr(f.local, 'site', None),
             cached=frame.f_locals.get('cached', False),
             config_encryption_key_present=bool(arg and arg.get('encryption_key')),
             config_admin_present=bool(arg and arg.get('admin_password')),
             config_matches_retained=bool(arg and matches_retained(arg.get('admin_password'))))
    elif event == 'return' and path.endswith('test_frappe_client.py') and name == 'TestFrappeClient':
        emit('auth_class_import', class_name=name, config_present=bool(f.conf.get('admin_password')),
             password_matches_config=frame.f_locals.get('PASSWORD') == f.conf.get('admin_password'),
             password_matches_retained=matches_retained(frame.f_locals.get('PASSWORD')))
    elif path.endswith('frappe/auth.py') and name in ('login', 'authenticate', 'fail', 'post_login'):
        data = {'operation': name + '_' + event, 'site': getattr(f.local, 'site', None)}
        if name == 'fail':
            reason = frame.f_locals.get('message')
            data['native_reason'] = reason if reason in REASONS else 'OTHER_NATIVE_REASON'
        emit('native_auth_operation', **data)
    elif path.endswith('frappe/utils/password.py') and name == 'update_password' and event == 'call':
        # Observe the native installation/test call, never call it ourselves.
        emit('native_password_write_call', administrator=frame.f_locals.get('user') == 'Administrator',
             passed_matches_retained=matches_retained(frame.f_locals.get('pwd')), caller=frames(frame.f_back))
    elif path.endswith('frappe/auth.py') and name == 'is_user_allowed' and event == 'return':
        tracker = frame.f_locals.get('self')
        emit('native_auth_tracker', allowed=arg,
             failed_count=frame.f_locals.get('login_failed_count'),
             max_failed_logins=tracker.max_failed_logins,
             lock_interval_seconds=tracker.lock_interval.total_seconds(),
             tracker_kind='administrator' if tracker.key == 'Administrator' else (
                 'loopback_ip' if tracker.key in ('127.0.0.1', '::1') else 'other_native_key'))
    elif event == 'call' and path.endswith('frappe/app.py') and name == 'handle_exception':
        exc = frame.f_locals.get('e')
        tb = getattr(exc, '__traceback__', None)
        trace = []
        while tb:
            trace.append({'file': tb.tb_frame.f_code.co_filename, 'line': tb.tb_lineno,
                          'function': tb.tb_frame.f_code.co_name})
            tb = tb.tb_next
        emit('native_http_exception', exception=type(exc).__name__, frames=trace,
             site=getattr(f.local, 'site', None), route=getattr(getattr(f.local, 'request', None), 'path', None))
    elif event == 'return' and path.endswith('frappe/app.py') and name == 'application':
        status = getattr(arg, 'status_code', None)
        if status is not None:
            emit('native_http_reply', status=status, site=getattr(f.local, 'site', None),
                 route=getattr(getattr(f.local, 'request', None), 'path', None),
                 location=redirect(arg.headers.get('Location', '')))
    elif path.endswith('workflow_action/workflow_action.py') and name == 'process_workflow_actions' and event == 'call':
        doc = frame.f_locals.get('doc')
        if doc and doc.doctype == 'ToDo':
            emit('native_todo_workflow_call', **context(f), caller=frames(frame))


def trace(frame, event, arg, emit):
    if (frame.f_code.co_name == 'cache_html_decorator' and
            frame.f_code.co_filename.endswith('frappe/website/utils.py')):
        f = sys.modules.get('frappe')
        if event in ('call', 'exception'):
            emit('native_cache_html', stage=event, **context(f), caller=frames(frame),
                 **({'exception': arg[0].__name__, 'exception_attribute': getattr(arg[1], 'name', None)}
                    if event == 'exception' else {}))
        return lambda fr, ev, ar: trace(fr, ev, ar, emit)
    if (frame.f_code.co_name == 'test_login_using_implicit_token' and
            frame.f_code.co_filename.endswith('frappe/tests/test_oauth20.py')):
        if event == 'line' and 'response_dict' in frame.f_locals:
            # Names/presence only; no values even on the successful path.
            emit('native_oauth_assertion_state', line=frame.f_lineno,
                 response_parameter_names=sorted(frame.f_locals['response_dict']),
                 access_token_present=bool(frame.f_locals['response_dict'].get('access_token')),
                 redirect_destination_present=frame.f_locals.get('redirect_destination') is not None)
        return lambda fr, ev, ar: trace(fr, ev, ar, emit)
    return None
