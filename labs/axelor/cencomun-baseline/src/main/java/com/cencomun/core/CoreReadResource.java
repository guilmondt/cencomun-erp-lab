package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.auth.AuthUtils;
import com.axelor.db.JpaSecurity;
import com.axelor.db.Model;
import com.axelor.db.Query;
import com.axelor.inject.Beans;
import com.axelor.rpc.filter.Filter;
import jakarta.ws.rs.BadRequestException;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.ForbiddenException;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotAuthorizedException;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Native Axelor-discovered REST resource for the shared LAB adapter search route. */
@Path("/ccm")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class CoreReadResource {
  private Model company(String code) {
    if (!"1".equals(System.getenv("CCM_CORE_LAB"))) throw new NotFoundException();
    if (AuthUtils.getUser() == null) throw new NotAuthorizedException("Session");
    if (!AuthUtils.hasRole(AuthUtils.getUser(), "CCM Reader", "CCM Operator", "CCM Manager", "CCM Director", "CCM Simulator", "CCM MCP"))
      throw new ForbiddenException("Core read role required");
    Model current = (Model) get(AuthUtils.getUser(), "activeCompany");
    if (current == null || code == null || !code.equals(get(current, "code")))
      throw new ForbiddenException("Company denied");
    Beans.get(JpaSecurity.class).check(JpaSecurity.AccessType.READ, type(NativeIndependentController.PROFILE));
    return current;
  }
  @GET
  @Path("/products/search")
  public Map<String, Object> search(@QueryParam("company_id") String companyCode,
      @QueryParam("q") @DefaultValue("") String text,
      @QueryParam("page") @DefaultValue("1") int page,
      @QueryParam("page_size") @DefaultValue("100") int size) {
    Model company = company(companyCode);
    if (page < 1 || size < 1 || size > 1000 || text.length() > 200) throw new BadRequestException("Invalid search bounds");
    String pattern = "%" + text.toLowerCase(Locale.ROOT) + "%";
    Query<Model> query = Query.of(type(NativeIndependentController.PROFILE)).filter(
        "self.company = ?1 AND (LOWER(self.product.code) LIKE ?2 OR LOWER(self.product.name) LIKE ?2 OR LOWER(self.supplierReference) LIKE ?2)", company, pattern);
    long count = query.count();
    List<Map<String, Object>> items = new ArrayList<>();
    int offset;
    try { offset = Math.multiplyExact(page - 1, size); }
    catch (ArithmeticException error) { throw new BadRequestException("Invalid search offset"); }
    for (Model profile : query.order("product.code").fetch(size, offset)) {
      Model product = (Model) get(profile, "product");
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", get(product, "code")); row.put("native_id", product.getId()); row.put("profile_id", profile.getId());
      row.put("name", get(product, "name"));
      row.put("marketplace_enabled", get(profile, "marketplaceEnabled")); row.put("cashea_enabled", get(profile, "casheaEnabled"));
      row.put("cashea_price", get(profile, "casheaPrice")); row.put("supplier_reference", get(profile, "supplierReference"));
      row.put("warranty_quantity", get(profile, "warrantyQuantity")); row.put("warranty_unit", get(profile, "warrantyUnit").toString());
      row.put("condition", get(profile, "condition").toString());
      items.add(row);
    }
    return Map.of("items", items, "total", count, "page", page, "page_size", size);
  }

  /** Read the generator's real source links under the existing native Invoice scope. */
  @GET @Path("/lab/invoice-links")
  public Map<String, Object> invoiceLinks(@QueryParam("company_id") String companyCode,
      @QueryParam("reference") String reference) {
    Model current = company(companyCode);
    if (reference == null || reference.isBlank() || reference.length() > 200)
      throw new BadRequestException("LAB invoice reference required");
    Class<Model> invoiceType = type("com.axelor.apps.account.db.Invoice");
    JpaSecurity security = Beans.get(JpaSecurity.class);
    security.check(JpaSecurity.AccessType.READ, invoiceType);
    Filter scope = security.getFilter(JpaSecurity.AccessType.READ, invoiceType);
    if (scope == null) throw new IllegalStateException("Expected scoped native Invoice read filter");
    List<Map<String, Object>> results = new ArrayList<>();
    for (Model invoice : Filter.and(scope, Filter.equals("externalReference", reference)).build(invoiceType).fetch(100)) {
      if (!current.getId().equals(((Model) get(invoice, "company")).getId()))
        throw new ForbiddenException("Invoice company denied");
      results.add(NativeInvoiceLinks.inspect(invoice));
    }
    return Map.of("actor", AuthUtils.getUser().getCode(), "reader_company_id", current.getId(),
        "invoices", results);
  }

  /** Diagnose the existing native reader filter without bypassing or broadening it. */
  @GET @Path("/lab/search/diagnostics")
  public Map<String, Object> diagnostics(@QueryParam("company_id") String companyCode,
      @QueryParam("name") String name) {
    Model current = company(companyCode);
    if (name == null || name.length() > 200) throw new BadRequestException("LAB name required");
    Class<Model> partner = type("com.axelor.apps.base.db.Partner");
    JpaSecurity security = Beans.get(JpaSecurity.class);
    security.check(JpaSecurity.AccessType.READ, partner);
    Filter scope = security.getFilter(JpaSecurity.AccessType.READ, partner);
    if (scope == null) throw new IllegalStateException("Expected scoped native Partner read filter");
    Query<Model> selected = Filter.and(scope, Filter.equals("name", name)).build(partner);
    return Map.of("actor", AuthUtils.getUser().getCode(), "company_id", current.getId(),
        "native_scope", scope.getQuery(), "native_params", scope.getParams(),
        "scoped_count", scope.build(partner).count(), "name_count", selected.count(),
        "native_partner_ids", selected.fetch(100).stream().map(Model::getId).toList());
  }
}
