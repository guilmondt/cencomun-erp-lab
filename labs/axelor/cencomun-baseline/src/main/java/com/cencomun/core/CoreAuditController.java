package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Read-only ORM metadata, durable native audit/outbox and recovery count evidence. */
public class CoreAuditController {
  public void inspect(ActionRequest request,ActionResponse response) {
    NativeIndependentController.fixtureAdmin();
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    Map<String,Object> result=new LinkedHashMap<>();result.put("company_id",company.getId());result.put("company_code",get(company,"code"));
    result.put("audit",list(CoreOrderService.DB+"CcmAudit","self.company = ?1",company).stream().sorted(java.util.Comparator.comparing(Model::getId)).map(a->{
      Map<String,Object> row=new LinkedHashMap<>();row.put("id",a.getId());row.put("actor",get(a,"actorCode"));row.put("actor_id",((Model)get(a,"actor")).getId());
      row.put("occurred_at",String.valueOf(get(a,"createdOn")));row.put("object_id",get(a,"objectRef"));
      for(String f:List.of("kind","correlation","reason","beforeState","afterState","rejected"))row.put(f,get(a,f));return row;
    }).toList());
    result.put("events",Beans.get(CoreOutboxService.class).inspect());
    result.put("actors",list("com.axelor.auth.db.User","self.code LIKE ?1","ccm-%").stream().map(u->Map.of(
        "id",u.getId(),"code",get(u,"code"),"active_company",get(get(u,"activeCompany"),"code"),
        "companies",((java.util.Set<Model>)get(u,"companySet")).stream().map(c->get(c,"code")).toList(),
        "roles",((java.util.Set<Model>)get(u,"roles")).stream().map(r->get(r,"name")).sorted(java.util.Comparator.comparing(Object::toString)).toList())).toList());
    result.put("models",List.of("CcmOrder","CcmOrderLine","CcmPurchase","CcmCashClose","CcmBankImport","CcmBankRow","CcmAudit","CcmRequestKey","CcmOutboxEvent","CcmRateAuthorization","CcmProductProfile").stream().map(name->{
      Class<Model> entity=type(CoreOrderService.DB+name);Map<String,Object> row=new LinkedHashMap<>();row.put("class",entity.getName());
      row.put("orm_entity",entity.isAnnotationPresent(jakarta.persistence.Entity.class));
      try {
        Class<?> repo=Class.forName(CoreOrderService.DB+"repo."+name+"Repository");row.put("repository",Beans.get(repo).getClass().getName());
      }catch(ClassNotFoundException error){throw new IllegalStateException("Native generated repository missing",error);}
      return row;
    }).toList());
    result.put("order_counts",Map.of("IDEM-CREATE",list(CoreOrderService.DB+"CcmOrder","self.company = ?1 AND self.functionalId = ?2",company,"IDEM-CREATE").stream().map(Model::getId).toList(),
        "IDEM-LOST",list(CoreOrderService.DB+"CcmOrder","self.company = ?1 AND self.functionalId = ?2",company,"IDEM-LOST").stream().map(Model::getId).toList()));
    result.put("core_lab_enabled","1".equals(System.getenv("CCM_CORE_LAB")));
    result.put("read_boundary","separate-http-after-business-commit-or-rollback");response.setValue("core_result",result);
  }
}
