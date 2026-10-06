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

OFFLINE = os.environ.get('CCM_OFFICIAL_OFFLINE') == '1'
OBSERVE = os.environ.get('CCM_OFFICIAL_OBSERVE') == '1'
OUTPUT = os.environ.get('CCM_OFFICIAL_OBSERVATION')
CURRENT = None
BUSY = False


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


def profile(frame, event, arg):
    global BUSY
    if BUSY or event != 'return':
        return
    function = frame.f_code.co_name
    filename = frame.f_code.co_filename
    if function == 'setup_module_map' and filename.endswith('frappe/__init__.py'):
        f = sys.modules.get('frappe')
        emit('module_map_return', include_all_apps=frame.f_locals.get('include_all_apps'),
             payments=f.local.module_app.get('payments'), app_modules=frame.f_locals.get('app_modules'),
             apps_read=frame.f_locals.get('apps'), db_name=f.local.conf.get('db_name'))
    elif function == 'get_exchange_rate' and filename.endswith('erpnext/setup/utils.py'):
        fields = ('from_currency', 'to_currency', 'transaction_date', 'args', 'entries')
        emit('fx_return', result=arg, **{k: frame.f_locals.get(k) for k in fields})
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


if OFFLINE or OBSERVE:
    sys.addaudithook(audit)
    emit('observer_started', offline=OFFLINE, upstream_functions_replaced=False)
    # This is transport observation/restriction, not an exchange-rate mock.
    import requests
    original_send = requests.sessions.Session.send

    def send(self, request, **kwargs):
        target = urlsplit(request.url)
        if OFFLINE and not loopback(target.hostname):
            emit('external_http_rejected', hostname=target.hostname, path=target.path)
            raise requests.exceptions.ConnectionError('Official offline reproduction: external HTTP prohibited')
        response = original_send(self, request, **kwargs)
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
