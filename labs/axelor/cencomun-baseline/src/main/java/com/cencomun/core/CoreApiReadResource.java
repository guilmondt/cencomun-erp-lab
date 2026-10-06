package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.axelor.db.JpaSecurity;
import com.axelor.inject.Beans;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.ForbiddenException;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.core.MediaType;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Company/role checked native reads for the same four neutral read operations. */
@Path("/ccm") @Produces(MediaType.APPLICATION_JSON)
public class CoreApiReadResource {
  static Model company(String code) {
    Model company;
    try {company=CoreOrderService.company(CoreOrderService.JSON.valueToTree(Map.of("company_id",code==null?"":code)));}
    catch(CoreFault error){throw new WebApplicationException(error.getMessage(),error.status);}
    if(CoreOrderService.roles().stream().noneMatch(Set.of("reader","operator","buyer","manager","director","simulator","mcp")::contains))throw new ForbiddenException("Core reader role required");
    return company;
  }
  @GET @Path("inventory/{productId}")
  public Map<String,Object> inventory(@PathParam("productId")String productCode,@QueryParam("company_id")String companyCode,@QueryParam("warehouse")String warehouseName) {
    Model company=company(companyCode),warehouse=one("com.axelor.apps.stock.db.StockLocation","self.company = ?1 AND self.name = ?2",company,warehouseName);
    if(warehouse==null)throw new ForbiddenException("Native inventory warehouse company denied");
    Model product=one("com.axelor.apps.base.db.Product","self.code = ?1",productCode);
    if(product==null||one(NativeIndependentController.PROFILE,"self.company = ?1 AND self.product = ?2",company,product)==null)throw new NotFoundException("Company product not found");
    Model stock=one("com.axelor.apps.stock.db.StockLocationLine","self.stockLocation = ?1 AND self.product = ?2",warehouse,product);
    if(stock==null)throw new NotFoundException("Native inventory line not found");
    BigDecimal onhand=(BigDecimal)get(stock,"currentQty"),reserved=(BigDecimal)get(stock,"reservedQty"),cost=(BigDecimal)get(stock,"avgPrice");
    Map<String,Object> result=new LinkedHashMap<>();result.put("product_id",productCode);result.put("warehouse",warehouseName);result.put("unit",get(get(product,"unit"),"name"));
    result.put("on_hand",onhand.stripTrailingZeros().toPlainString());result.put("reserved",reserved.stripTrailingZeros().toPlainString());result.put("available",onhand.subtract(reserved).stripTrailingZeros().toPlainString());
    result.put("value",MoneyPolicy.money(onhand.multiply(cost)).toPlainString());result.put("unit_cost",MoneyPolicy.money(cost).toPlainString());
    result.put("native_stock_line_id",stock.getId());result.put("native_warehouse_id",warehouse.getId());result.put("native_product_id",product.getId());return result;
  }
  @GET @Path("customers/{customerId}/balance")
  public Map<String,Object> balance(@PathParam("customerId")String customerCode,@QueryParam("company_id")String companyCode) {
    Model company=company(companyCode),customer=one("com.axelor.apps.base.db.Partner","self.partnerSeq = ?1 AND ?2 MEMBER OF self.companySet",customerCode,company);
    if(customer==null)throw new NotFoundException("Native company customer not found");
    Map<String,BigDecimal> sums=new java.util.TreeMap<>();List<Long> invoices=new ArrayList<>();
    for(Model invoice:list("com.axelor.apps.account.db.Invoice","self.company = ?1 AND self.partner = ?2 AND self.statusSelect = ?3 AND self.operationTypeSelect = ?4",company,customer,3,3)) {
      String currency=String.valueOf(get(get(invoice,"currency"),"codeISO"));sums.merge(currency,(BigDecimal)get(invoice,"amountRemaining"),BigDecimal::add);invoices.add(invoice.getId());
    }
    if(sums.isEmpty())sums.put("USD",BigDecimal.ZERO);Map<String,String> amounts=new LinkedHashMap<>();sums.forEach((c,v)->amounts.put(c,MoneyPolicy.money(v).toPlainString()));
    return Map.of("customer_id",customerCode,"balances",amounts,"native_customer_id",customer.getId(),"native_invoice_ids",invoices);
  }
  @GET @Path("cash/status")
  public Map<String,Object> cash(@QueryParam("company_id")String companyCode,@QueryParam("id")String id) {
    Model company=company(companyCode);Beans.get(JpaSecurity.class).check(JpaSecurity.AccessType.READ,type(CoreOrderService.DB+"CcmCashClose"));
    List<Model> closes=list(CoreOrderService.DB+"CcmCashClose",id==null?"self.company = ?1":"self.company = ?1 AND self.functionalId = ?2",id==null?new Object[]{company}:new Object[]{company,id});
    if(closes.isEmpty())return Map.of("state","EMPTY","channels",List.of(),"cashea_pending","0.00","cashea_received","0.00");
    Model close=closes.stream().max(java.util.Comparator.comparing(Model::getId)).orElseThrow();Map<String,Object> view=CoreCashService.view(close);
    Map<String,String> expected=(Map<String,String>)view.get("expectedAmounts"),observed=(Map<String,String>)view.get("observedAmounts"),differences=(Map<String,String>)view.get("differences");
    Map<String,Object> source=(Map<String,Object>)view.get("sourceSnapshot");List<Map<String,Object>> channels=new ArrayList<>();
    for(String channel:List.of("USD","VES","POS","TRANSFER"))channels.add(Map.of("channel",channel,"currency",channel.equals("VES")?"VES":"USD","expected",expected.get(channel),"observed",observed.get(channel),"difference",differences.get(channel)));
    Map<String,Object> result=new LinkedHashMap<>();result.put("id",get(close,"functionalId"));result.put("state",view.get("state"));result.put("channels",channels);
    Map<String,Object> pending=(Map<String,Object>)source.get("pending_invoice");result.put("cashea_pending",pending==null?"0.00":MoneyPolicy.money(new BigDecimal(pending.get("remaining").toString())).toPlainString());
    result.put("cashea_received",pending==null?"0.00":MoneyPolicy.money(new BigDecimal(pending.get("paid").toString())).toPlainString());result.put("native_closing_id",close.getId());
    result.put("confirmed_by",view.get("confirmed_by"));result.put("confirmed_at",view.get("confirmed_at"));return result;
  }
}
