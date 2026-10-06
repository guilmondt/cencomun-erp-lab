package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Read-only separate-request evidence; audit of a rejected request commits only after rollback. */
public class CoreFinanceInspection {
  static Map<String,Object> business(Model company,String id) {
    Map<String,Object> result=new LinkedHashMap<>();
    Model purchase=one(CoreOrderService.DB+"CcmPurchase","self.company = ?1 AND self.functionalId = ?2",company,id);
    Model close=one(CoreOrderService.DB+"CcmCashClose","self.company = ?1 AND self.functionalId = ?2",company,id);
    result.put("purchase",purchase==null?Map.of():Beans.get(CorePurchaseService.class).view(purchase));
    result.put("cash_close",close==null?Map.of():CoreCashService.view(close));return result;
  }
  public Map<String,Object> inspect(String id) {
    NativeIndependentController.fixtureAdmin();Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    Map<String,Object> result=business(company,id);result.put("native_cash",CoreCashService.source(company));
    result.put("bank_rows",list(CoreOrderService.DB+"CcmBankRow","self.company = ?1",company).stream().sorted(java.util.Comparator.comparing(Model::getId)).map(CoreBankService::view).toList());
    result.put("bank_imports",list(CoreOrderService.DB+"CcmBankImport","self.company = ?1",company).stream().map(m->Map.of("id",m.getId(),"file_hash",get(m,"fileHash"),"native_statement_id",((Model)get(m,"bankStatement")).getId())).toList());
    result.put("keys",list(CoreOrderService.DB+"CcmRequestKey","self.company = ?1 AND self.objectRef = ?2",company,id).stream().map(k->Map.of("id",k.getId(),"domain",get(k,"domain"),"key",get(k,"requestKey"))).toList());
    result.put("events",list(CoreOrderService.DB+"CcmOutboxEvent","self.company = ?1 AND self.objectRef = ?2",company,id).stream().map(e->Map.of("id",e.getId(),"event_key",get(e,"eventKey"),"kind",get(e,"kind"),"delivered",get(e,"delivered"),"attempts",get(e,"attempts"))).toList());
    result.put("audit",list(CoreOrderService.DB+"CcmAudit","self.company = ?1 AND self.objectRef = ?2",company,id).stream().sorted(java.util.Comparator.comparing(Model::getId)).map(a->{
      Map<String,Object> row=new LinkedHashMap<>();row.put("id",a.getId());row.put("actor",get(a,"actorCode"));row.put("actor_id",((Model)get(a,"actor")).getId());row.put("created_on",String.valueOf(get(a,"createdOn")));
      for(String field:List.of("kind","correlation","reason","beforeState","afterState","rejected"))row.put(field,get(a,field));return row;
    }).toList());
    result.put("read_boundary","separate-http-after-business-commit-or-rollback");return result;
  }
  @Transactional(rollbackOn=Exception.class)
  public void rejected(JsonNode input,String reason) {
    if(AuthUtils.getUser()==null)return;
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1",input.path("company_id").asText());if(company==null)return;
    String id=input.path("id").asText("invalid");Map<String,Object> snapshot=business(company,id);
    CoreRecordSupport.audit(company,id,"finance.denied",snapshot,snapshot,reason,input.path("request_key").asText("invalid-request"),true);
  }
}
