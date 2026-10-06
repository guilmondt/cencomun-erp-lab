package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.cencomun.core.db.CcmOrder;
import com.cencomun.core.db.CcmOrderState;
import com.cencomun.core.db.CcmAudit;
import com.axelor.apps.sale.db.SaleOrder;
import com.axelor.apps.stock.db.StockMove;
import com.axelor.apps.account.db.Invoice;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeAll;
import com.axelor.inject.Beans;
import com.axelor.db.json.JsonReferenceCascader;
import com.axelor.db.json.JsonReferenceUpdater;
import com.google.inject.AbstractModule;
import com.google.inject.Guice;

class NativeOrderModelTest {
  @BeforeAll static void initializeRepositoryConstructorOnly() {
    // Real native helpers; these guard tests never invoke JPA/save/cascade.
    // Actual listener/DI/DB acceptance is the unmodified full-stack application.
    Guice.createInjector(new AbstractModule() {
      protected void configure() {
        bind(JsonReferenceCascader.class).toProvider(JsonReferenceCascader::new);
        bind(JsonReferenceUpdater.class).toProvider(JsonReferenceUpdater::new);
        bind(Beans.class).asEagerSingleton();
      }
    });
  }
  @Test void generatedStateCannotRepresentAnUnknownValue() {
    CcmOrder nativeMapped=new CcmOrder();
    com.axelor.db.mapper.Mapper mapper=com.axelor.db.mapper.Mapper.of(CcmOrder.class);
    mapper.set(nativeMapped,"state","REVIEWED");assertEquals(CcmOrderState.REVIEWED,nativeMapped.getState());
    IllegalArgumentException denied=assertThrows(IllegalArgumentException.class,()->mapper.set(nativeMapped,"state","UNKNOWN-LAB"));
    Throwable root=denied;while(root.getCause()!=null)root=root.getCause();
    assertTrue(root.getMessage().contains("UNKNOWN-LAB"));assertTrue(root.getMessage().contains("CcmOrderState"));
    assertTrue(java.util.Arrays.stream(root.getStackTrace()).anyMatch(f->f.getClassName().equals("com.axelor.db.ValueEnum") && f.getMethodName().equals("of")));
    assertEquals(CcmOrderState.REVIEWED,nativeMapped.getState());
    CcmOrder order=new CcmOrder();assertEquals(CcmOrderState.NEW,order.getState());
  }
  @Test void economicDocumentReferencesAreNativeTypedForeignKeys() throws Exception {
    assertEquals(SaleOrder.class,CcmOrder.class.getMethod("getSaleOrder").getReturnType());
    assertEquals(StockMove.class,CcmOrder.class.getMethod("getDelivery").getReturnType());
    assertEquals(Invoice.class,CcmOrder.class.getMethod("getInvoice").getReturnType());
  }
  @Test void genericRepositorySaveDoesNotGainWorkflowPrivilege() {
    CoreFault denied=assertThrows(CoreFault.class,()->new CcmOrderWorkflowRepository().save(new CcmOrder()));
    assertEquals(403,denied.status);
  }
  @Test void semanticAuditCannotBeEditedEvenWithinWorkflowScope() {
    CcmAudit audit=new CcmAudit();audit.setId(1L);
    try(CoreWriteScope scope=CoreWriteScope.enter()) {
      assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->new CcmAuditWorkflowRepository().save(audit)).getResponse().getStatus());
      assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->new CcmAuditWorkflowRepository().remove(audit)).getResponse().getStatus());
    }
    assertThrows(CoreFault.class,CoreWriteScope::require);
  }
}
