package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import jakarta.persistence.LockModeType;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Durable native outbox. Delivery retries repeat transport, never ERP economics. */
public class CoreOutboxService {
  static URI endpoint(String value) {
    URI uri=URI.create(value);
    if(!"http".equals(uri.getScheme())||!List.of("127.0.0.1","localhost").contains(uri.getHost())||uri.getPort()<1||uri.getPort()>65535
        ||!"/events".equals(uri.getPath())||uri.getUserInfo()!=null||uri.getQuery()!=null||uri.getFragment()!=null)
      throw new CoreFault(422,"Private LAB consumer endpoint required");return uri;
  }
  public List<Map<String,Object>> inspect() {
    NativeIndependentController.fixtureAdmin();
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    return list(CoreOrderService.DB+"CcmOutboxEvent","self.company = ?1",company).stream().sorted(java.util.Comparator.comparing(Model::getId)).map(e->Map.<String,Object>of(
        "id",e.getId(),"event_id",get(e,"eventKey"),"object_id",get(e,"objectRef"),"kind",get(e,"kind"),
        "payload",get(e,"payload"),"delivered",get(e,"delivered"),"attempts",get(e,"attempts"))).toList();
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> dispatch(JsonNode input) {
    NativeIndependentController.fixtureAdmin();URI target=endpoint(input.path("consumer_url").asText());
    boolean replay=input.path("replay").asBoolean(false);Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    List<Map<String,Object>> attempts=new ArrayList<>();int delivered=0,failed=0;
    HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    for(Model event:list(CoreOrderService.DB+"CcmOutboxEvent",replay?"self.company = ?1":"self.company = ?1 AND self.delivered = false",company)) {
      JPA.em().refresh(event,LockModeType.PESSIMISTIC_WRITE);
      int status=503;String error="";
      try {
        HttpRequest request=HttpRequest.newBuilder(target).timeout(Duration.ofSeconds(15)).header("Content-Type","application/json")
            .POST(HttpRequest.BodyPublishers.ofString((String)get(event,"payload"))).build();
        status=client.send(request,HttpResponse.BodyHandlers.discarding()).statusCode();
      }catch(Exception problem){error=problem.getClass().getSimpleName()+": "+problem.getMessage();if(problem instanceof InterruptedException)Thread.currentThread().interrupt();}
      set(event,"attempts",((Integer)get(event,"attempts"))+1);
      if(status==200){set(event,"delivered",true);delivered++;}else failed++;
      save(event);attempts.add(Map.of("event_id",get(event,"eventKey"),"http_status",status,"error",error));
    }
    return Map.of("delivered",delivered,"failed",failed,"attempts",attempts);
  }
}
