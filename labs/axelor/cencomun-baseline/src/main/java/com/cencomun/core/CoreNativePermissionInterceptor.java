package com.cencomun.core;

import org.aopalliance.intercept.MethodInterceptor;
import org.aopalliance.intercept.MethodInvocation;

/** Guice extension: native controllers cannot bypass the LAB permission matrix. */
public final class CoreNativePermissionInterceptor implements MethodInterceptor {
  @Override public Object invoke(MethodInvocation invocation) throws Throwable {
    if("1".equals(System.getenv("CCM_CORE_LAB")))CoreNativeScope.require();
    return invocation.proceed();
  }
}
