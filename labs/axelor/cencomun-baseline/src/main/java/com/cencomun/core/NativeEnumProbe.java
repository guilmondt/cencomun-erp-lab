package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.axelor.db.mapper.Mapper;
import com.google.inject.persist.Transactional;
import java.util.LinkedHashMap;
import java.util.Map;

/** Native Mapper enum conversion with a valid persistence control; both units always roll back. */
public class NativeEnumProbe {
  public static final class Progress {
    public final Map<String,Object> evidence=new LinkedHashMap<>();
    public String stage="native-order-read";
  }
  public static final class ControlRollback extends RuntimeException {
    public final Map<String,Object> evidence;
    ControlRollback(Map<String,Object> evidence) { super("Native valid enum persisted and re-read; diagnostic rollback"); this.evidence=evidence; }
  }
  @Transactional(rollbackOn=Exception.class)
  public void execute(String id, String rawState, Progress p) {
    NativeIndependentController.fixtureAdmin();
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    Model order=one(CoreOrderService.DB+"CcmOrder","self.company = ?1 AND self.functionalId = ?2",company,id);
    if(order==null)throw new IllegalStateException("Enum probe requires an existing native order fixture");
    Mapper mapper=Mapper.of(EntityHelperClass(order));
    p.evidence.put("property","state"); p.evidence.put("raw_value",rawState);
    p.evidence.put("enum_type",mapper.getProperty("state").getJavaType().getName());
    p.evidence.put("model_id",order.getId());p.evidence.put("native_mapper","com.axelor.db.mapper.Mapper.set");
    p.stage="native-enum-conversion";
    mapper.set(order,"state",rawState);
    p.evidence.put("mapped_state",get(order,"state").toString());
    p.stage="native-repository-save-and-flush";
    order=save(order);JPA.em().flush();Long nativeId=order.getId();JPA.em().clear();
    order=JPA.find(type(CoreOrderService.DB+"CcmOrder"),nativeId);
    p.evidence.put("persisted_state",get(order,"state").toString());p.evidence.put("persisted_native_id",order.getId());
    p.stage="native-enum-persisted-and-reloaded";
    throw new ControlRollback(new LinkedHashMap<>(p.evidence));
  }
  private Class<?> EntityHelperClass(Model model) { return com.axelor.db.EntityHelper.getEntityClass(model); }
}
