#!/usr/bin/env python3
"""Read-only browser checks after the five-sale UI acceptance script."""
from pathlib import Path
import os,json
from playwright.sync_api import sync_playwright,expect
from evidence import EvidenceRun
from snapshots import capture,digest
from http_client import Client
p=Path(os.environ['CCM_PILOT_RESULTS']);actors=json.loads(Path(os.environ['CCM_PILOT_ACTORS_FILE']).read_text());refs=json.loads((p/'refs.json').read_text());base=os.environ.get('CCM_PILOT_URL','http://127.0.0.1:18080/axelor-erp/');proof={}
with EvidenceRun(p/'views.json') as evidence:
 a=Client(password=os.environ.get('CCM_PILOT_ADMIN_PASSWORD','admin'))
 before=capture(a);evidence.data.update(roles=proof,snapshot_before=before);evidence.save()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
   for role in ['operator','supervisor']:
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    def observe(response):
     if '/ws/action' in response.url:
      r=response.json()
      if r.get('status')==-1:errors.append({'url':response.url,'response':r})
    page.on('response',observe);page.goto(base);page.locator('[name=username]').fill('pilot-'+role);page.locator('[name=password]').fill(actors[role]);page.get_by_role('button',name='Sign in',exact=True).click()
    page.get_by_text('Cencomun · Piloto',exact=True).click();page.get_by_text('Productos e inventario',exact=True).click()
    expect(page.get_by_text('[P001] Equipo ficticio Alfa',exact=True)).to_be_visible()
    expect(page.get_by_role('button').filter(has_text='add')).to_have_count(0)
    expect(page.get_by_role('button').filter(has_text='edit')).to_have_count(0)
    page.screenshot(path=str(p/('catalog-'+role+'.png')))
    page.get_by_text('[P001] Equipo ficticio Alfa',exact=True).dblclick()
    expect(page.get_by_text('18.0000000000',exact=True)).to_be_visible()
    expect(page.get_by_role('button').filter(has_text='add')).to_have_count(0)
    expect(page.get_by_role('button').filter(has_text='edit')).to_have_count(0)
    page.screenshot(path=str(p/('stock-'+role+'.png')))
    page.get_by_text('Entrega y liquidación',exact=True).click()
    expect(page.get_by_text(refs['pending'],exact=True)).to_be_visible()
    page.screenshot(path=str(p/('pending-'+role+'.png')))
    page.get_by_text(refs['pending'],exact=True).dblclick()
    expect(page.locator('[data-testid="field:state"]:visible input')).to_have_value('RESERVED')
    if role=='operator':expect(page.get_by_role('button',name='Cancelar y devolver inicial cobrada',exact=True)).not_to_be_visible()
    expect(page.get_by_role('button',name='Registrar liquidación Cashea',exact=True)).not_to_be_visible()
    page.get_by_text('Cierre de caja',exact=True).click();page.get_by_text('CONFIRMED',exact=True).dblclick()
    expect(page.locator('[data-testid="field:counted"]:visible input')).to_have_value('164.00')
    expect(page.get_by_role('button',name='Confirmar cierre inmutable',exact=True)).not_to_be_visible()
    page.screenshot(path=str(p/('closed-reentered-'+role+'.png')))
    page.reload(wait_until='networkidle')
    expect(page.locator('[data-testid="field:counted"]:visible input')).to_have_value('164.00',timeout=15000)
    expect(page.locator('[data-testid="field:state"]:visible input')).to_have_value('CONFIRMED')
    expect(page.get_by_role('button',name='Confirmar cierre inmutable',exact=True)).not_to_be_visible()
    page.screenshot(path=str(p/('closed-reloaded-'+role+'.png')))
    assert not errors,errors
    proof[role]={'catalog_new_edit_absent':True,'native_stock_P001':18,'pending_before_delivery_visible':True,'settlement_not_offered_before_delivery':True,'confirmed_close_reentered_counted':'164.00','confirmed_close_reloaded_counted':'164.00','unexpected_action_errors':errors}
    page.close()
   browser.close()
 finally:
  after=capture(a);evidence.data.update(snapshot_after=after,snapshot_hashes={'before':digest(before),'after':digest(after)});evidence.save()
  evidence.check('read-only UI and reload preserve all economic fields',before==after)
print('Both profiles: catalog, stock, pending delivery, immutable close reentry/reload and unchanged economic snapshots PASS')
