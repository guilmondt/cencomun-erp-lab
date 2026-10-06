package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthService;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.google.inject.persist.Transactional;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Synthetic fixture setup only. Business calls authenticate each actual LAB actor. */
public class CoreOrderController {
  public void actors(ActionRequest request, ActionResponse response) {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result",Beans.get(CoreOrderController.class).prepareActors());
  }
  @Transactional(rollbackOn = Exception.class)
  public Map<String,Object> prepareActors() {
    NativeIndependentController.fixtureAdmin();
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", "CCM-LAB-001");
    if (company == null) throw new IllegalStateException("Catalog must be committed first");
    Model foreign = one("com.axelor.apps.base.db.Company", "self.code = ?1", "OTHER-LAB");
    if (foreign == null) foreign = record("com.axelor.apps.base.db.Company", "code", "OTHER-LAB", "name", "Foreign synthetic LAB", "currency", get(company,"currency"));
    for (String roleName : CoreOrderService.ROLE_NAMES.values())
      if (one("com.axelor.auth.db.Role", "self.name = ?1", roleName) == null)
        record("com.axelor.auth.db.Role", "name", roleName);
    List<Map<String,Object>> users = new ArrayList<>();
    for (Map.Entry<String,String> entry : CoreOrderService.ROLE_NAMES.entrySet()) {
      String key = entry.getKey(); Model role = one("com.axelor.auth.db.Role", "self.name = ?1",entry.getValue());
      if (role == null) role = record("com.axelor.auth.db.Role","name",entry.getValue());
      HashSet<Model> grants = new HashSet<>(get(role,"permissions") == null ? Set.of() : (java.util.Set<Model>)get(role,"permissions"));
      if (!key.equals("other")) {
        for (String name:List.of("CcmOrder","CcmOrderLine","CcmAudit","CcmRequestKey","CcmOutboxEvent","CcmPurchase","CcmCashClose","CcmBankImport","CcmBankRow")) {
          // All roles read company-scoped evidence; no generic REST business writes.
          String condition = name.equals("CcmOrderLine") ? "self.coreOrder.company.id = ?" : "self.company.id = ?";
          String permissionName = "ccm.lab.order.read."+name;
          Model permission = one("com.axelor.auth.db.Permission","self.name = ?1",permissionName);
          if (permission == null) permission=record("com.axelor.auth.db.Permission","name",permissionName,
              "object",CoreOrderService.DB+name,"canRead",true,"canWrite",false,"canCreate",false,"canRemove",false,
              "condition",condition,"conditionParams","__user__.activeCompany.id");
          grants.add(permission);
        }
      }
      set(role,"permissions",grants); save(role);
      Model user=one("com.axelor.auth.db.User","self.code = ?1","ccm-"+key);
      if(user==null) user=record("com.axelor.auth.db.User","code","ccm-"+key,"name","Synthetic Core "+key,
          "password",AuthService.getInstance().encrypt("CoreLab-"+key+"-2026!"),"email",key+"@example.invalid");
      HashSet<Model> roles=new HashSet<>(get(user,"roles") == null ? Set.of() : (java.util.Set<Model>)get(user,"roles")); roles.add(role);
      if(key.equals("selfbuyer")) for(String extra:List.of("operator","buyer"))
        roles.add(one("com.axelor.auth.db.Role","self.name = ?1",CoreOrderService.ROLE_NAMES.get(extra)));
      Model active=key.equals("other")?foreign:company;
      set(user,"roles",roles); set(user,"blocked",false); set(user,"activeCompany",active);
      set(user,"companySet",new HashSet<>(List.of(active))); save(user);
      users.add(Map.of("id",user.getId(),"code",get(user,"code"),"role",entry.getValue(),"company_id",active.getId()));
    }
    return Map.of("users",users,"scope","Synthetic disposable CI users; existing grants preserved; generic writes denied");
  }
  private String id(ActionRequest request) {
    String id=String.valueOf(request.getContext().get("case_id"));
    if(!id.matches("[A-Z0-9][A-Z0-9-]{0,79}")) throw new IllegalArgumentException("Invalid synthetic fixture ID");
    return id;
  }
  public void prepare(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin(); String id=id(request);
    NativeGateService.Progress p=new NativeGateService.Progress();
    // Interceptor commits this catalog/configuration transaction before returning.
    Beans.get(NativeGateService.class).prepare(p,id);
    response.setValue("core_result",Map.of("case",id,"phase","catalog-committed","evidence",p.evidence));
  }
  public void seed(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin(); String id=id(request);
    NativeGateService service=Beans.get(NativeGateService.class);
    Map<String,Object> current=service.inspect(id);
    boolean replay=!((List<?>)current.get("stock_move_ids")).isEmpty();
    if(!replay)service.seed(new NativeGateService.Progress(),id);
    response.setValue("core_result",Map.of("case",id,"replayed",replay,"native_export",service.inspect(id)));
  }
  public void negativeCost(ActionRequest request, ActionResponse response) {
    NativeIndependentController.fixtureAdmin(); String id=id(request);
    Map<String,Object> control=costProbe(id,new java.math.BigDecimal("30.00"));
    Map<String,Object> invalid=costProbe(id,new java.math.BigDecimal("-0.01"));
    // Python reviewer identifies the native cost-specific validator; no class-only PASS flag.
    response.setValue("core_result",Map.of("case",id,"valid_control",control,"invalid_attempt",invalid));
  }
  private Map<String,Object> costProbe(String id,java.math.BigDecimal cost) {
    NativeNegativeCostProbe.Progress p=new NativeNegativeCostProbe.Progress();
    try { Beans.get(NativeNegativeCostProbe.class).execute(id,cost,p);throw new IllegalStateException("Probe must roll back"); }
    catch(Exception error) {
      Throwable root=error;while(root.getCause()!=null && root.getCause()!=root)root=root.getCause();
      Map<String,Object> proof=new java.util.LinkedHashMap<>(p.evidence);
      proof.put("stage",p.stage);proof.put("diagnostic_rollback_only",root instanceof NativeNegativeCostProbe.NativeAcceptedCost);
      proof.put("error_type",root.getClass().getName());proof.put("error",String.valueOf(root.getMessage()));
      proof.put("native_stack",java.util.Arrays.stream(root.getStackTrace()).filter(f->f.getClassName().startsWith("com.axelor.")||f.getClassName().startsWith("com.cencomun.")).limit(18).map(StackTraceElement::toString).toList());
      return proof;
    }
  }
  public void enumProbe(ActionRequest request, ActionResponse response) {
    NativeIndependentController.fixtureAdmin();String id=id(request);
    response.setValue("core_result",Map.of("case",id,"valid_control",enumProbe(id,"REVIEWED"),"invalid_attempt",enumProbe(id,"UNKNOWN-LAB")));
  }
  private Map<String,Object> enumProbe(String id,String state) {
    NativeEnumProbe.Progress p=new NativeEnumProbe.Progress();
    try { Beans.get(NativeEnumProbe.class).execute(id,state,p);throw new IllegalStateException("Probe must roll back"); }
    catch(Exception error) {
      Throwable root=error;while(root.getCause()!=null && root.getCause()!=root)root=root.getCause();
      Map<String,Object> proof=new java.util.LinkedHashMap<>(p.evidence);
      proof.put("stage",p.stage);proof.put("diagnostic_rollback_only",root instanceof NativeEnumProbe.ControlRollback);
      proof.put("error_type",root.getClass().getName());proof.put("error",String.valueOf(root.getMessage()));
      proof.put("native_stack",java.util.Arrays.stream(root.getStackTrace()).filter(f->f.getClassName().startsWith("com.axelor.")||f.getClassName().startsWith("com.cencomun.")).limit(18).map(StackTraceElement::toString).toList());
      return proof;
    }
  }
  public void inspect(ActionRequest request, ActionResponse response) {
    NativeIndependentController.fixtureAdmin(); response.setValue("core_result",Beans.get(CoreOrderService.class).inspect(id(request)));
  }
}
