package com.cencomun.core;

import com.axelor.db.JPA;
import java.lang.reflect.Proxy;
import java.util.Map;
import java.util.LinkedHashMap;

/** Actual per-session Hibernate JDBC execution metrics, confined to LAB requests.
 * Authentication and response serialization are outside this service boundary.
 * No SQL text, arguments, secrets, global counters or sampling are recorded.
 */
final class CoreRequestMetrics {
  private final long started=System.nanoTime();
  private long jdbcStarted,dbNanos,queries;
  private CoreRequestMetrics() {
    try {
      Class<?> sessionType=Class.forName("org.hibernate.engine.spi.SessionImplementor");
      Object session=JPA.em().unwrap(sessionType);
      Object manager=sessionType.getMethod("getEventListenerManager").invoke(session);
      Class<?> listenerType=Class.forName("org.hibernate.SessionEventListener");
      Object listener=Proxy.newProxyInstance(listenerType.getClassLoader(),new Class<?>[]{listenerType},(proxy,method,args)-> {
        switch(method.getName()) {
          case "jdbcExecuteStatementStart", "jdbcExecuteBatchStart" -> {queries++;jdbcStarted=System.nanoTime();}
          case "jdbcExecuteStatementEnd", "jdbcExecuteBatchEnd" -> {dbNanos+=System.nanoTime()-jdbcStarted;}
          case "equals" -> {return proxy==args[0];}
          case "hashCode" -> {return System.identityHashCode(proxy);}
          case "toString" -> {return "Cencomun per-request JDBC observer";}
          default -> {}
        }
        return null;
      });
      Object array=java.lang.reflect.Array.newInstance(listenerType,1);java.lang.reflect.Array.set(array,0,listener);
      Class.forName("org.hibernate.engine.spi.SessionEventListenerManager").getMethod("addListener",array.getClass()).invoke(manager,array);
    } catch(ReflectiveOperationException error) {throw new IllegalStateException("Pinned native JDBC metrics unavailable",error);}
  }
  static CoreRequestMetrics begin() {return "1".equals(System.getenv("CCM_CORE_LAB"))?new CoreRequestMetrics():null;}
  static Map<String,Object> measured(java.util.function.Supplier<Map<String,Object>> action) {
    CoreRequestMetrics metrics=begin();Map<String,Object> result=action.get();
    if(metrics==null)return result;
    result=new LinkedHashMap<>(result);result.put("_meta",metrics.finish());return result;
  }
  Map<String,Object> finish() {
    return Map.of("server_ms",(System.nanoTime()-started)/1000000.0,"query_count",queries,"db_ms",dbNanos/1000000.0,
        "source","Hibernate SessionEventListener JDBC execution callbacks",
        "boundary","authenticated resource/service/transaction; excludes authentication, serialization and isolated native sequence threads");
  }
}
