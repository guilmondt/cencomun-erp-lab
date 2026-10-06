"""Opt-in observation and loopback-only transport for official reproductions.

No business function, fixture, rate, validator or expected result is replaced.
The socket audit hook forbids external DNS/connections even through a proxy.
HTTP observation records status/path only, never bodies, query tokens or headers.
"""
import ipaddress
import json
import os
import sys
import time
import unittest
import re
import hashlib
from urllib.parse import urlsplit
import threading

OFFLINE = os.environ.get('CCM_OFFICIAL_OFFLINE') == '1'
OBSERVE = os.environ.get('CCM_OFFICIAL_OBSERVE') == '1'
OUTPUT = os.environ.get('CCM_OFFICIAL_OBSERVATION')
CURRENT = None
BUSY = False


def safe_url(url):
    parsed = urlsplit(str(url))
    host = parsed.hostname
    return {'url': (parsed.scheme + '://' + str(host) +
                    (':' + str(parsed.port) if parsed.port else '') + parsed.path),
            'hostname': host, 'port': parsed.port or (443 if parsed.scheme == 'https' else 80),
            'path': parsed.path}


def journal_state(doc, stage):
    if doc is not None and doc.doctype == 'Journal Entry':
        emit('journal_state', stage=stage,
             **{k: doc.get(k) for k in ('name', 'docstatus', 'voucher_type', 'company',
                'company_currency', 'posting_date', 'multi_currency', 'total_debit',
                'total_credit', 'difference', 'reversal_of')},
             accounts=[{k: row.get(k) for k in ('idx', 'account', 'account_currency',
                'exchange_rate', 'debit', 'credit', 'debit_in_account_currency',
                'credit_in_account_currency', 'reference_type', 'reference_name')}
                for row in doc.get('accounts', [])])


def adapter_state():
    requests_module = sys.modules.get('requests')
    if requests_module is None:
        return {}
    function = requests_module.adapters.HTTPAdapter.send
    return {'module': getattr(function, '__module__', type(function).__module__),
            'function': getattr(function, '__qualname__', type(function).__qualname__),
            'source_file': getattr(getattr(function, '__code__', None), 'co_filename', None)}


def registered_requests(mock):
    rows = getattr(mock, 'registered', ())
    if callable(rows):
        rows = rows()
    return [{'method': r.method, **safe_url(r.url)} for r in rows
            if isinstance(getattr(r, 'url', None), str)]


def native_responses_mock_active():
    """Respect an upstream in-memory mock only when it cannot pass through.

    Do not invoke registry.find/matches (which can consume registrations).
    No mock is installed here and no response/rate is constructed here.
    """
    responses = sys.modules.get('responses')
    requests_module = sys.modules.get('requests')
    if responses is None or requests_module is None:
        return False
    function = requests_module.adapters.HTTPAdapter.send
    code = getattr(function, '__code__', None)
    if (getattr(function, '__module__', None) != 'responses' or code is None
            or code.co_filename != responses.__file__):
        return False
    for cell in getattr(function, '__closure__', ()) or ():
        mock = cell.cell_contents
        if isinstance(mock, responses.RequestsMock):
            return (not mock.passthru_prefixes and
                    not any(row.passthrough for row in mock.registered()))
    return False


def suite_ids(suite):
    if isinstance(suite, unittest.TestCase):
        return [suite.id()]
    if isinstance(suite, unittest.TestSuite):
        return [identifier for child in suite for identifier in suite_ids(child)]
    return []


def emit(kind, **data):
    if OUTPUT:
        with open(OUTPUT, 'a') as stream:
            stream.write(json.dumps({'kind': kind, 'pid': os.getpid(), 'epoch': time.time(),
                                     'test': CURRENT, **data}, default=str) + '\n')


def loopback(host):
    if host in ('localhost', '::1'):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def audit(event, args):
    if not OFFLINE:
        return
    host = None
    if event == 'socket.getaddrinfo':
        host = args[0]
        # Native Werkzeug binds 0.0.0.0. Resolving this literal bind address
        # is local; it neither queries DNS nor authorizes outbound connections.
        if host in ('0.0.0.0', '::'):
            return
    elif event == 'socket.connect' and isinstance(args[1], tuple):
        host = args[1][0]
    if host is not None and not loopback(host):
        emit('external_transport_rejected', transport=event)
        raise PermissionError('Official offline reproduction forbids external transport')


def snapshot(stage):
    global BUSY
    if BUSY:
        return
    f = sys.modules.get('frappe')
    if f is None:
        return
    BUSY = True
    try:
        if not f.db:
            return
        data = {'stage': stage, 'site': f.local.site, 'user': f.session.user,
                'module_payments': f.local.module_app.get('payments'),
                'installed_apps': f.get_installed_apps(), 'apps_on_bench': f.get_all_apps(),
                'cached_app_modules': f.cache.get_value('app_modules'),
                'request_is_none': getattr(f.local, 'request', None) is None}
        data['url_config'] = {k: f.conf.get(k) for k in ('host_name', 'hostname',
            'http_port', 'webserver_port', 'developer_mode', 'restart_supervisor_on_update',
            'restart_systemd_on_update')}
        data['http_adapter_send'] = adapter_state()
        if 'erpnext' in data['installed_apps']:
            s = f.get_doc('Currency Exchange Settings')
            a = f.get_doc('Accounts Settings')
            data['fx_settings'] = {k: s.get(k) for k in ('disabled', 'service_provider', 'api_endpoint', 'use_http')}
            data['fx_accounts'] = {k: a.get(k) for k in ('allow_stale', 'stale_days', 'allow_pegged_currencies_exchange_rates')}
            data['fx_rows'] = f.get_all('Currency Exchange', fields=['date', 'from_currency', 'to_currency', 'exchange_rate', 'for_buying', 'for_selling'])
            if CURRENT and ('test_bom.' in CURRENT or 'test_work_order_manufacture_with_material_consumption' in CURRENT):
                data['bom_item_2'] = f.get_all('BOM Item', filters={'item_code': '_Test Item 2', 'docstatus': 1}, fields=['parent', 'rate', 'base_rate', 'qty'])
                data['bins_item_2'] = f.get_all('Bin', filters={'item_code': '_Test Item 2'}, fields=['warehouse', 'actual_qty', 'stock_value', 'valuation_rate'])
        emit('native_state', **data)
    except Exception as exc:
        emit('observation_error', stage=stage, exception=type(exc).__name__)
    finally:
        BUSY = False


def profile_event(frame, event, arg):
    global BUSY
    if BUSY:
        return
    function = frame.f_code.co_name
    filename = frame.f_code.co_filename
    if CURRENT and event in ('call', 'return'):
        if filename.endswith('journal_entry/journal_entry.py') and function in (
            'set_exchange_rate', 'set_amounts_in_company_currency',
            'set_total_debit_credit', 'validate_total_debit_and_credit', 'before_submit'):
            journal_state(frame.f_locals.get('self'), function + '_' + event)
        elif event == 'call' and function == 'submit' and filename.endswith('model/document.py'):
            journal_state(frame.f_locals.get('self'), 'before_submit_call')
        elif event == 'return' and function == 'get_exchange_rate' and filename.endswith('journal_entry/journal_entry.py'):
            emit('journal_fx_return', result=arg, **{k: frame.f_locals.get(k) for k in (
                'posting_date', 'account', 'account_currency', 'company', 'reference_type',
                'reference_name', 'debit', 'credit', 'exchange_rate')})
    if event != 'return':
        return
    if function == 'loadTestsFromModule' and filename.endswith('unittest/loader.py'):
        emit('native_module_discovery', module=getattr(frame.f_locals.get('module'), '__name__', None),
             test_ids=suite_ids(arg))
    if function in ('start', 'stop', 'reset') and filename.endswith('responses/__init__.py'):
        doc = frame.f_locals.get('self')
        emit('native_mock_transition', operation=function, adapter=adapter_state(),
             registered=registered_requests(doc))
    if function == 'setup_module_map' and filename.endswith('frappe/__init__.py'):
        f = sys.modules.get('frappe')
        emit('module_map_return', include_all_apps=frame.f_locals.get('include_all_apps'),
             payments=f.local.module_app.get('payments'), app_modules=frame.f_locals.get('app_modules'),
             apps_read=frame.f_locals.get('apps'), db_name=f.local.conf.get('db_name'))
    elif function == 'get_exchange_rate' and filename.endswith('erpnext/setup/utils.py'):
        fields = ('from_currency', 'to_currency', 'transaction_date', 'args', 'entries', 'filters')
        emit('fx_return', result=arg, **{k: frame.f_locals.get(k) for k in fields})
    elif function == 'get_url' and filename.endswith('frappe/utils/data.py'):
        emit('native_get_url', **safe_url(arg))
    elif function == 'init_request' and filename.endswith('frappe/app.py'):
        f = sys.modules.get('frappe')
        emit('native_http_served', site=getattr(f.local, 'site', None))
    elif function == 'log_error' and filename.endswith('frappe/utils/error.py') and arg and arg.method == 'Unable to fetch exchange rate':
        raw = arg.error or ''
        emit('native_fx_error_log', name=arg.name, creation=arg.creation,
             method=arg.method, raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
             frames=re.findall(r'^  File .+$', raw, re.M),
             terminal_exception=raw.splitlines()[-1] if raw else '')
    elif function == 'get_routing' and filename.endswith('bom/bom.py'):
        doc = frame.f_locals.get('self')
        if doc:
            emit('bom_routing_state', **{k: doc.get(k) for k in ('name', 'routing', 'currency', 'company', 'conversion_rate', 'quantity')})
    elif function == '_validate_non_negative' and filename.endswith('model/document.py'):
        doc = frame.f_locals.get('self')
        if doc and doc.doctype == 'Stock Entry':
            emit('stock_entry_validation', items=[{k: r.get(k) for k in ('idx', 'item_code', 'qty', 'basic_rate', 'amount', 's_warehouse', 't_warehouse', 'secondary_item_type')} for r in doc.items])


def profile(frame, event, arg):
    try:
        profile_event(frame, event, arg)
    except Exception as exc:
        # Observation must never turn a native import or test into a failure.
        emit('observation_error', stage='profile', exception=type(exc).__name__)


if OFFLINE or OBSERVE:
    sys.addaudithook(audit)
    emit('observer_started', offline=OFFLINE, upstream_functions_replaced=False)
    # This is transport observation/restriction, not an exchange-rate mock.
    import requests
    original_send = requests.sessions.Session.send

    def send(self, request, **kwargs):
        target = urlsplit(request.url)
        emit('http_attempt', method=request.method, adapter=adapter_state(), **safe_url(request.url))
        mocked = native_responses_mock_active()
        if OFFLINE and not loopback(target.hostname) and not mocked:
            emit('external_http_rejected', hostname=target.hostname, path=target.path)
            raise requests.exceptions.ConnectionError('Official offline reproduction: external HTTP prohibited')
        if mocked:
            emit('native_mock_dispatch', method=request.method, **safe_url(request.url))
        try:
            response = original_send(self, request, **kwargs)
        except requests.exceptions.RequestException as exc:
            emit('http_exception', method=request.method, exception=type(exc).__name__,
                 connection_refused='Connection refused' in str(exc),
                 refused_by_responses='Connection refused by Responses' in str(exc),
                 os_errno111='[Errno 111]' in str(exc), **safe_url(request.url))
            raise
        emit('http_response', method=request.method, hostname=target.hostname, path=target.path,
             status=response.status_code, domain_forbidden=response.text.strip() == 'Domain forbidden',
             proxy_used=bool(kwargs.get('proxies')))
        return response

    requests.sessions.Session.send = send
    if OBSERVE:
        original_start, original_stop = unittest.TestResult.startTest, unittest.TestResult.stopTest

        def start(self, test):
            global CURRENT
            CURRENT = test.id()
            snapshot('before_test')
            return original_start(self, test)

        def stop(self, test):
            global CURRENT
            snapshot('after_test')
            emit('test_stopped')
            CURRENT = None
            return original_stop(self, test)

        unittest.TestResult.startTest, unittest.TestResult.stopTest = start, stop
        sys.setprofile(profile)
        threading.setprofile(profile)
