package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;

import com.axelor.apps.base.db.Partner;
import com.axelor.apps.account.db.Invoice;
import com.axelor.db.Model;
import com.axelor.db.Query;
import com.axelor.rpc.filter.Filter;
import com.axelor.rpc.filter.JPQLFilter;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;

/** Exercises the pinned native composer; does not claim DB/reader acceptance. */
class NativePermissionFilterTest {
  private static Object queryProperty(Query<?> query, String name) throws Exception {
    Method method = Query.class.getDeclaredMethod(name);
    method.setAccessible(true); // Observe native output, never replace the composer or binding.
    return method.invoke(query);
  }

  private static <T extends Model> void composed(Class<T> model, String condition,
      String field, String value) throws Exception {
    Filter scope = new JPQLFilter(condition, 42L);
    Query<T> query = Filter.and(scope, Filter.equals(field, value)).build(model);
    String text = (String) queryProperty(query, "getFilter");
    assertTrue(text.contains("?1"), text);
    assertTrue(text.contains("?2"), text);
    assertFalse(text.contains("?11"), text);
    assertArrayEquals(new Object[] {42L, value}, (Object[]) queryProperty(query, "getParams"));
    assertEquals("(" + condition + ")", scope.getQuery()); // Native JPQLFilter wraps the unchanged predicate.
    assertTrue(text.contains("= ?1"), text);
    assertTrue(text.contains(field + " = ?2"), text);
  }

  @Test void readerNameKeepsCompanyBeforeString() throws Exception {
    composed(Partner.class, NativeIndependentController.PARTNER_CONDITION, "name", "Cliente ficticio Alfa");
  }
  @Test void readerPhoneKeepsCompanyBeforeString() throws Exception {
    composed(Partner.class, NativeIndependentController.PARTNER_CONDITION, "mobilePhone", "+12025550101");
  }
  @Test void readerInvoiceKeepsCompany() throws Exception {
    composed(Invoice.class, NativeIndependentController.COMPANY_CONDITION, "externalReference", "CCM-CO00");
  }
  @Test void oldIndexedPermissionReproducesNativeDoubleNumbering() throws Exception {
    Query<Partner> query = Filter.and(new JPQLFilter(
        NativeIndependentController.PARTNER_CONDITION.replace("?", "?1"), 42L),
        Filter.equals("name", "Cliente ficticio Alfa")).build(Partner.class);
    String text = (String) queryProperty(query, "getFilter");
    // Observe the final native query, not just the intermediate ?11: name
    // incorrectly reuses the company binding, comparing a String with Long.
    assertTrue(text.contains("c.id = ?1"), text);
    assertTrue(text.contains("name = ?1"), text);
    assertArrayEquals(new Object[] {42L, "Cliente ficticio Alfa"}, (Object[]) queryProperty(query, "getParams"));
  }
  @Test void directQueryRetainsExplicitIndexes() throws Exception {
    Query<Partner> query = Query.of(Partner.class).filter("self.id = ?1 AND self.name = ?2", 42L, "Cliente ficticio Alfa");
    String text = (String) queryProperty(query, "getFilter");
    assertTrue(text.contains("?1") && text.contains("?2"), text);
    assertFalse(text.contains("?11"), text);
    assertArrayEquals(new Object[] {42L, "Cliente ficticio Alfa"}, (Object[]) queryProperty(query, "getParams"));
  }
}
