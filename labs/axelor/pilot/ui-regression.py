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
receipts=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    def actor(role):
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.goto(base);page.locator('[name=username]').fill('pilot-'+role)
        page.locator('[name=password]').fill(secrets[role]);page.get_by_role('button',name='Sign in',exact=True).click()
        page.get_by_text('Cencomun · Piloto',exact=True).click();return page
    def click(page,label,action,success=True):
        with page.expect_response(lambda r:r.url.endswith('/ws/action') and action in (r.request.post_data or ''),timeout=120000) as seen:
            page.get_by_role('button',name=label,exact=True).click()
        result=seen.value.json();receipts.append({'action':action,'request':json.loads(seen.value.request.post_data),'response':result})
        print(action,result.get('status'),flush=True)
        (out/'receipts.json').write_text(json.dumps(receipts,indent=2))
        assert (result.get('status')==0)==success,result
        return result
    def widget(page,name):
        return page.locator('[data-testid="field:'+name+'"]:visible')
    def field(page,name,value):
        node=widget(page,name).locator('input')
        if not node.is_editable(): page.get_by_role('button').filter(has_text='edit').first.click()
        node.fill(str(value));node.press('Tab')
    def open_sale(page,ref):
        page.get_by_role('button',name='Grid',exact=True).click();page.get_by_text(ref,exact=True).dblclick()
    supervisor=actor('supervisor');operator=actor('operator')
    supervisor.get_by_text('Cierre de caja',exact=True).click()
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
    refs['cash']=new_sale(products)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect');click(operator,'Entregar productos','ccm-pilot-deliver')
    refs['cashea']=new_sale(products,45)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect');click(operator,'Entregar productos','ccm-pilot-deliver')
    expect(operator.get_by_role('button',name='Registrar liquidación Cashea',exact=True)).not_to_be_visible()
    supervisor.get_by_text('Venta y pedido',exact=True).click();supervisor.get_by_text(refs['cashea'],exact=True).dblclick()
    click(supervisor,'Registrar liquidación Cashea','ccm-pilot-settle')
    refs['web']=new_sale([('P004','Producto ficticio 4'),('P005','Producto ficticio 5')],54,True,2)
    # Regression: native UI sends temporary guide as `guide`, not `$guide`.
    field(operator,'$guide','UI-REGRESSION-WEB');click(operator,'Entregar productos','ccm-pilot-deliver')
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    open_sale(supervisor,refs['web']);click(supervisor,'Registrar liquidación Cashea','ccm-pilot-settle')
    refs['pending']=new_sale([('P006','Producto ficticio 6')],36)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    refs['cancel']=new_sale([('P007','Producto ficticio 7')],42)
    click(operator,'Registrar cobro inicial real','ccm-pilot-collect')
    open_sale(supervisor,refs['cancel']);field(supervisor,'$reason','Cliente ficticio desiste; devolución física realizada')
    click(supervisor,'Cancelar y devolver inicial cobrada','ccm-pilot-cancel')
    supervisor.get_by_text('Cierre de caja',exact=True).click()
    click(supervisor,'Consultar efectivo esperado','ccm-pilot-preview')
    field(supervisor,'$cashCountedInput','164');click(supervisor,'Confirmar cierre inmutable','ccm-pilot-close',False)
    field(supervisor,'$cashDifferenceReason','Faltante ficticio de 1 USD en recuento');click(supervisor,'Confirmar cierre inmutable','ccm-pilot-close')
    expect(widget(supervisor,'state').locator('input')).to_have_value('CONFIRMED')
    expect(widget(supervisor,'expected').locator('input')).to_have_value('165.00')
    expect(widget(supervisor,'counted').locator('input')).to_have_value('164.00')
    expect(widget(supervisor,'difference').locator('input')).to_have_value('-1.00')
    supervisor.screenshot(path=str(out/'closed.png'))
    (out/'refs.json').write_text(json.dumps(refs,indent=2));(out/'receipts.json').write_text(json.dumps(receipts,indent=2))
    browser.close()
print('UI workflows completed; independently verify native accounting/stock before acceptance.')
