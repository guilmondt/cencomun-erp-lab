package com.cencomun.core;

import com.axelor.auth.AuthUtils;
import com.axelor.rpc.ActionRequest;
import java.util.Set;
import org.aopalliance.intercept.MethodInterceptor;
import org.aopalliance.intercept.MethodInvocation;

/** Dedicated pilot accounts may execute only their published pilot actions.
 * Native read REST remains scoped by native permissions; economic services and
 * repositories retain their independent guards. Administrator is not affected.
 */
public final class PilotActionGuard implements MethodInterceptor {
  private static final Set<String> ALLOWED=Set.of(
      "ccm-pilot-defaults","ccm-pilot-flags","ccm-pilot-line","ccm-pilot-create",
      "ccm-pilot-collect","ccm-pilot-deliver","ccm-pilot-cancel","ccm-pilot-settle",
      "ccm-pilot-open","ccm-pilot-preview","ccm-pilot-close",
      "ccm-pilot-catalog-open","ccm-pilot-sales-open","ccm-pilot-pending-open",
      "ccm-pilot-cash-open","ccm-pilot-stock-view",
      "com.axelor.meta.web.MetaController:moreAttrs");
  static void check(String action) {
    if(action==null)throw new CoreFault(403,"Pilot action required");
    // AOP appends its read-only dynamic-attribute loader to onNew actions.
    for(String item:action.split(",",-1))
      if(!ALLOWED.contains(item))throw new CoreFault(403,"Pilot action denied: use the dedicated pilot screens");
  }
  @Override public Object invoke(MethodInvocation invocation) throws Throwable {
    var user=AuthUtils.getUser();
    if(user!=null && (AuthUtils.hasRole(user,"CCM Pilot Operator")||AuthUtils.hasRole(user,"CCM Pilot Supervisor")))
      check(((ActionRequest)invocation.getArguments()[0]).getAction());
    return invocation.proceed();
  }
}
