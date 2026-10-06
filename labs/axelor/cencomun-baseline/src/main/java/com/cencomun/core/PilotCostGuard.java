package com.cencomun.core;

import static com.cencomun.core.NativeAccess.get;
import java.math.BigDecimal;
import java.util.List;
import org.aopalliance.intercept.MethodInterceptor;
import org.aopalliance.intercept.MethodInvocation;

/** Supported Guice extension, enabled only in the pilot runtime. */
public final class PilotCostGuard implements MethodInterceptor {
  @Override public Object invoke(MethodInvocation invocation) throws Throwable {
    if("1".equals(System.getenv("CCM_PILOT_LAB"))) {
      for(Object argument:invocation.getArguments()) {
        if(!(argument instanceof com.axelor.db.Model))continue;
        Class<?> type=com.axelor.db.EntityHelper.getEntityClass(argument);
        String name=type.getSimpleName();
        String full=type.getName();
        boolean economic=full.startsWith("com.axelor.apps.account.db.")||full.startsWith("com.axelor.apps.stock.db.")
            ||full.startsWith("com.axelor.apps.sale.db.")||full.startsWith("com.axelor.apps.purchase.db.")||name.equals("Product");
        var user=com.axelor.auth.AuthUtils.getUser();
        if(economic && user!=null && (com.axelor.auth.AuthUtils.hasRole(user,"CCM Pilot Operator")
            ||com.axelor.auth.AuthUtils.hasRole(user,"CCM Pilot Supervisor")))CoreNativeScope.require();
        if(name.equals("Product"))check(argument,"costPrice","purchasePrice");
        if(name.equals("StockMoveLine"))check(argument,"unitPriceUntaxed","unitPriceTaxed","wapPrice");
        if(name.equals("StockMove")) {
          Object lines=get(argument,"stockMoveLineList");
          // Native stock batches clear the persistence context. An uninitialized
          // detached collection contains no caller edits; inspect its managed copy.
          if(!org.hibernate.Hibernate.isInitialized(lines))
            lines=NativeAccess.list("com.axelor.apps.stock.db.StockMoveLine","self.stockMove.id = ?1",((com.axelor.db.Model)argument).getId());
          if(lines instanceof List<?> rows)for(Object line:rows)check(line,"unitPriceUntaxed","unitPriceTaxed","wapPrice");
        }
        if(name.equals("PurchaseOrderLine"))check(argument,"price");
        if(name.equals("StockLocationLine"))check(argument,"avgPrice");
      }
    }
    return invocation.proceed();
  }
  static void check(Object model,String... fields) {
    for(String field:fields) {
      BigDecimal amount=(BigDecimal)get(model,field);
      if(amount!=null && amount.signum()<0)throw new CoreFault(422,"Pilot negative cost forbidden: "+field);
    }
  }
}
