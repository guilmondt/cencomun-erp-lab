#!/usr/bin/env python3
"""Destructive only to an explicitly disposable, freshly seeded pilot database.
Run against localhost after prepare/seed. Credentials stay in an external JSON.
Creates real native sales through Chromium; no business writes through REST.
"""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

base=os.environ.get('CCM_PILOT_URL','http://127.0.0.1:18080/axelor-erp/').rstrip('/')+'/'
if os.environ.get('CCM_PILOT_DISPOSABLE')!='1':
    raise SystemExit('Set CCM_PILOT_DISPOSABLE=1 only for an isolated fresh fixture database')
secrets=json.loads(Path(os.environ['CCM_PILOT_ACTORS_FILE']).read_text())
out=Path(os.environ.get('CCM_PILOT_RESULTS','/tmp/ccm-pilot-ui'));out.mkdir(parents=True,exist_ok=True)
resume_web=os.environ.get('CCM_PILOT_RESUME_THROUGH_WEB')=='1'
resume=resume_web or os.environ.get('CCM_PILOT_RESUME_FIRST')=='1'
receipts=json.loads((out/'receipts.json').read_text()) if resume else []
network_actions=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    def record_action(response):
        if '/ws/action' in response.url:
            network_actions.append({'url':response.url,'request':json.loads(response.request.post_data or '{}'),'response':response.json()})
            (out/'network-actions.json').write_text(json.dumps(network_actions,indent=2))
    def actor(role):
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.on('response',record_action)
        page.goto(base);page.locator('[name=username]').fill('pilot-'+role)
        page.locator('[name=password]').fill(secrets[role]);page.get_by_role('button',name='Sign in',exact=True).click()
        page.get_by_text('Cencomun · Piloto',exact=True).click();return page
    def click(page,label,action,success=True):
        page.wait_for_load_state('networkidle')
        with page.expect_response(lambda r:r.url.endswith('/ws/action') and action in (r.request.post_data or ''),timeout=120000) as seen:
            button=page.get_by_role('button',name=label,exact=True)
            if action=='ccm-pilot-create': button.dblclick()
            else: button.click()
        result=seen.value.json();receipts.append({'action':action,'request':json.loads(seen.value.request.post_data),'response':result})
        print(action,result.get('status'),flush=True)
        (out/'receipts.json').write_text(json.dumps(receipts,indent=2))
        assert (result.get('status')==0)==success,result
        return result
    def widget(page,name):
        return page.locator('[data-testid="field:'+name+'"]:visible')
    def field(page,name,value):
        page.wait_for_load_state('networkidle')
        node=widget(page,name).locator('input')
        if not node.is_editable(): page.get_by_role('button').filter(has_text='edit').first.click()
        node.fill(str(value));node.press('Tab');page.wait_for_load_state('networkidle')
        actual=node.input_value()
        if isinstance(value,(int,float)) or name in ('$cashCountedInput',):
            from decimal import Decimal
            assert Decimal(actual.replace(',',''))==Decimal(str(value)),(name,actual,value)
        else: assert actual==str(value),(name,actual,value)
    def open_sale(page,ref):
        global supervisor
        page.close()
        supervisor=actor('supervisor')
        supervisor.get_by_text('Venta y pedido',exact=True).click()
        supervisor.get_by_text(ref,exact=True).dblclick()
    supervisor=actor('supervisor');operator=actor('operator')
    supervisor.get_by_text('Cierre de caja',exact=True).click()
    if resume: supervisor.get_by_text('OPEN',exact=True).dblclick()
    else:
        supervisor.get_by_role('button').filter(has_text='add').first.click()
        click(supervisor,'Abrir sesión de caja','ccm-pilot-open')
    def new_sale(products,financed=0,web=False,shipping=0):
        page=operator;page.get_by_text('Venta y pedido',exact=True).click()
        page.get_by_role('button').filter(has_text='add').first.click()
        widget(page,'customer').get_by_role('combobox').fill('C001')
        page.get_by_text('C001 - Cliente ficticio Alfa',exact=True).click()
        for code,name in products:
            page.get_by_role('button').filter(has_text='add').last.click()
            page.get_by_text('['+code+'] '+name,exact=True).click()
            widget(page,'qty').locator('input').fill('1');widget(page,'qty').locator('input').press('Enter')
        page.wait_for_load_state('networkidle')
        if financed:
            widget(page,'kind').get_by_role('combobox').click();page.get_by_text('Cashea',exact=True).click();field(page,'financed',financed)
        if web:
            widget(page,'channel').get_by_role('combobox').click();page.get_by_text('Web',exact=True).click();field(page,'shipping',shipping)
        ref=widget(page,'reference').locator('input').input_value()
        click(page,'Registrar pedido','ccm-pilot-create')
        expect(page.get_by_role('button',name='Cancelar y devolver inicial cobrada',exact=True)).not_to_be_visible()
        return ref
    products=[('P001','Equipo ficticio Alfa'),('P002','Accesorio ficticio Beta')]
    refs={}
    if resume:
        from http_client import Client
        existing=Client(password=os.environ.get('CCM_PILOT_ADMIN_PASSWORD','admin')).request('/ws/rest/com.cencomun.core.db.CcmPilotSale/search',{'limit':10})
        records={r['id']:r for r in existing['data']}
        assert existing['total']==(3 if resume_web else 1) and records[1]['state']=='PAID' and float(records[1]['gross'])==75
        refs['cash']=records[1]['reference']
        if resume_web:
            assert records[2]['state']=='SETTLED' and records[3]['state']=='DELIVERED' and records[3]['initialVoucher']
            refs['cashea']=records[2]['reference'];refs['web']=records[3]['reference']
    else:
        refs['cash']=new_sale(products)
        click(operator,'Entregar productos','ccm-pilot-deliver')
        open_sale(supervisor,refs['cash'])
        expect(widget(supervisor,'state').locator('input')).to_have_value('DELIVERED')
        expect(supervisor.get_by_role('button',name='Registrar liquidación Cashea',exact=True)).not_to_be_visible()
        supervisor.screenshot(path=str(out/'cash-unpaid-no-cashea-button.png'))
        click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    if not resume_web:
        refs['cashea']=new_sale(products,45)
        click(operator,'Registrar cobro inicial real','ccm-pilot-collect');click(operator,'Entregar productos','ccm-pilot-deliver')
        expect(operator.get_by_role('button',name='Registrar liquidación Cashea',exact=True)).not_to_be_visible()
        open_sale(supervisor,refs['cashea'])
        click(supervisor,'Registrar liquidación Cashea','ccm-pilot-settle')
        refs['web']=new_sale([('P004','Producto ficticio 4'),('P005','Producto ficticio 5')],54,True,2)
        # Regression: native UI sends temporary guide as `guide`, not `$guide`.
        field(operator,'$guide','UI-REGRESSION-WEB');click(operator,'Entregar productos','ccm-pilot-deliver')
        click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    open_sale(supervisor,refs['web']);click(supervisor,'Registrar liquidación Cashea','ccm-pilot-settle')
    refs['pending']=new_sale([('P006','Producto ficticio 6')],36)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    operator.get_by_text('Entrega y liquidación',exact=True).click()
    expect(operator.get_by_text(refs['pending'],exact=True)).to_be_visible()
    operator.screenshot(path=str(out/'pending-before-delivery-operator.png'))
    refs['cancel']=new_sale([('P007','Producto ficticio 7')],42)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    open_sale(supervisor,refs['cancel']);field(supervisor,'$reason','Cliente ficticio desiste; devolución física realizada')
    click(supervisor,'Cancelar y devolver inicial cobrada','ccm-pilot-cancel')
    supervisor.get_by_text('Cierre de caja',exact=True).click()
    supervisor.get_by_text('OPEN',exact=True).dblclick()
    click(supervisor,'Consultar efectivo esperado','ccm-pilot-preview')
    field(supervisor,'$cashCountedInput','164');click(supervisor,'Confirmar cierre inmutable','ccm-pilot-close',False)
    field(supervisor,'$cashDifferenceReason','Faltante ficticio de 1 USD en recuento');click(supervisor,'Confirmar cierre inmutable','ccm-pilot-close')
    expect(widget(supervisor,'state').locator('input')).to_have_value('CONFIRMED')
    expect(widget(supervisor,'expected').locator('input')).to_have_value('165.00')
    expect(widget(supervisor,'counted').locator('input')).to_have_value('164.00')
    expect(widget(supervisor,'difference').locator('input')).to_have_value('-1.00')
    supervisor.screenshot(path=str(out/'closed.png'))
    unexpected=[x for x in network_actions if x['response'].get('status')==-1 and x['request'].get('action')!='ccm-pilot-close']
    assert not unexpected,unexpected
    (out/'refs.json').write_text(json.dumps(refs,indent=2));(out/'receipts.json').write_text(json.dumps(receipts,indent=2))
    browser.close()
print('UI workflows completed; independently verify native accounting/stock before acceptance.')
