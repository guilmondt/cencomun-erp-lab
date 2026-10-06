package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.util.*;
import org.aopalliance.intercept.MethodInterceptor;
import org.aopalliance.intercept.MethodInvocation;

/** Exact tax-inclusive per-line policy, only inside authenticated pilot invoicing.
 * Replaces only native grouped-base tax comparison, never balance/posting checks.
 * No tolerance, persisted adjustment, or change to the historical oracle.
 */
public final class PilotInvoiceTaxGuard implements MethodInterceptor {
  record Expected(long company,Map<String,BigDecimal> amounts) {}
  private static final ThreadLocal<Expected> ACTIVE=new ThreadLocal<>();
  static Scope enter(Model company,JsonNode input) {
    if(ACTIVE.get()!=null)throw new IllegalStateException("Nested pilot tax scope");
    Map<String,BigDecimal> costs=new HashMap<>();
    input.get("lines").forEach(line->costs.put(line.get("product_id").asText(),BigDecimal.ZERO));
    ACTIVE.set(new Expected(company.getId(),MoneyPolicy.calculate(input,costs)));return new Scope();
  }
  static final class Scope implements AutoCloseable {public void close(){ACTIVE.remove();}}
  @Override public Object invoke(MethodInvocation call) throws Throwable {
    Expected expected=ACTIVE.get();
    if(expected==null)return call.proceed();
    Model move=(Model)call.getArguments()[0];
    if(move==null || get(move,"invoice")==null)return call.proceed();
    check(move,expected.company(),expected.amounts());return null;
  }
  static void check(Model move,long company,Map<String,BigDecimal> expected) {
    if(((Model)get(move,"company")).getId()!=company)throw new CoreFault(422,"Pilot tax company mismatch");
    BigDecimal debit=BigDecimal.ZERO,credit=BigDecimal.ZERO;
    Map<String,BigDecimal> observed=new HashMap<>();
    for(Object line:(List<?>)get(move,"moveLineList")) {
      String code=(String)get(get(line,"account"),"code");
      if(!Set.of("CCM-AR","CCM-REVENUE","CCM-TAX").contains(code))throw new CoreFault(422,"Unexpected pilot invoice account");
      BigDecimal d=(BigDecimal)get(line,"debit"),c=(BigDecimal)get(line,"credit");
      debit=debit.add(d);credit=credit.add(c);
      observed.merge(code,code.equals("CCM-AR")?d.subtract(c):c.subtract(d),BigDecimal::add);
    }
    if(debit.compareTo(credit)!=0)throw new CoreFault(422,"Pilot invoice move is not balanced");
    for(var pair:Map.of("CCM-AR","gross","CCM-REVENUE","revenue","CCM-TAX","tax").entrySet())
      if(observed.getOrDefault(pair.getKey(),BigDecimal.ZERO).compareTo(expected.get(pair.getValue()))!=0)
        throw new CoreFault(422,"Pilot per-line tax policy mismatch: "+pair.getKey());
  }
}
