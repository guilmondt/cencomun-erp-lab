package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.LinkedHashMap;

/** Shared durable records, called inside the authenticated business transaction. */
final class CoreRecordSupport {
  static String key(JsonNode input) {
    String key=input.path("request_key").asText();
    if(key.isBlank() || key.length()>180)throw new CoreFault(422,"Stable request key required");return key;
  }
  static Map<String,Object> replay(Model company,String domain,JsonNode input) {
    Model key=one(CoreOrderService.DB+"CcmRequestKey","self.company = ?1 AND self.domain = ?2 AND self.requestKey = ?3",company,domain,key(input));
    if(key==null)return null;
    if(!CoreOrderService.hash(input).equals(get(key,"payloadHash")))throw new CoreFault(409,"Idempotency payload conflict");
    try { Map<String,Object> result=CoreOrderService.JSON.readValue((String)get(key,"result"),Map.class);result.put("replayed",true);return result; }
    catch(java.io.IOException error){throw new IllegalStateException("Invalid persisted request result",error);}
  }
  static Map<String,Object> remember(Model company,String domain,JsonNode input,Map<String,Object> result) {
    result=new LinkedHashMap<>(result);result.put("replayed",false);
    record(CoreOrderService.DB+"CcmRequestKey","company",managed(company),"domain",domain,"requestKey",key(input),
        "payloadHash",CoreOrderService.hash(input),"objectRef",input.path("id").asText(),"result",CoreOrderService.encode(result));return result;
  }
  static void audit(Model company,String id,String kind,Map<String,Object> before,Map<String,Object> after,String reason,String correlation,boolean denied) {
    if(reason==null || reason.isBlank())throw new CoreFault(422,"Semantic reason required");
    record(CoreOrderService.DB+"CcmAudit","company",managed(company),"actor",AuthUtils.getUser(),"actorCode",AuthUtils.getUser().getCode(),
        "objectRef",id,"kind",kind,"beforeState",CoreOrderService.encode(before),"afterState",CoreOrderService.encode(after),
        "reason",reason,"correlation",correlation,"rejected",denied);
  }
  static void event(Model company,String id,String kind,String suffix,Map<String,Object> payload,String correlation,Model order) {
    String eventId=kind+":"+id+":"+suffix;
    Object occurred=call(service("com.axelor.apps.base.service.app.AppBaseService"),"getTodayDateTime",company);
    Map<String,Object> envelope=new LinkedHashMap<>();envelope.put("schema_version",1);envelope.put("event_id",eventId);
    envelope.put("type",kind);envelope.put("object_id",id);envelope.put("company_id",get(company,"code"));
    envelope.put("actor",AuthUtils.getUser().getCode());envelope.put("occurred_at",occurred.toString());envelope.put("correlation_id",correlation);envelope.put("data",payload);
    record(CoreOrderService.DB+"CcmOutboxEvent","company",managed(company),"coreOrder",order,"objectRef",id,"eventKey",eventId,
        "kind",kind,"payload",CoreOrderService.encode(envelope));
  }
  private CoreRecordSupport(){}
}
