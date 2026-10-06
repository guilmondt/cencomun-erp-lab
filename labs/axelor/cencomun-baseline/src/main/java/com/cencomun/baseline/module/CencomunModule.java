package com.cencomun.baseline.module;

import com.axelor.app.AxelorModule;

/** Supported Cencomun repository bindings; independent AOP profile has no native entities. */
public class CencomunModule extends AxelorModule {
  @Override @SuppressWarnings({"rawtypes", "unchecked"})
  protected void configure() {
    for(String name : new String[]{"CcmOrder","CcmOrderLine","CcmRequestKey","CcmOutboxEvent","CcmAudit","CcmPurchase","CcmCashClose","CcmBankImport","CcmBankRow"}) {
      try {
        Class repository=Class.forName("com.cencomun.core.db.repo."+name+"Repository");
        Class extension=Class.forName("com.cencomun.core."+name+"WorkflowRepository");
        bind(repository).to(extension);
      } catch(ClassNotFoundException missing) {
        if("1".equals(System.getenv("CCM_AXELOR_FULL_STACK")))
          throw new IllegalStateException("Native Core repository binding missing: "+name,missing);
      }
    }
  }
}
