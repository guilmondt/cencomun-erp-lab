package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import jakarta.persistence.LockModeType;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Purchase approval policy wraps the fixed native create/request/validate/cancel/draft workflows. */
public class CorePurchaseService {
  static final String PURCHASE="com.axelor.apps.purchase.db.";
  static final LocalDate DATE=LocalDate.of(2026,10,1);
  private String id(JsonNode input) {
    String id=input.path("id").asText();if(!id.matches("[A-Z0-9][A-Z0-9-]{0,79}"))throw new CoreFault(422,"Invalid purchase ID");return id;
  }
  private BigDecimal amount(JsonNode input) {
    try { BigDecimal value=new BigDecimal(input.path("amount").asText());MoneyPolicy.positiveMoney(value);return value; }
    catch(IllegalArgumentException error){throw new CoreFault(422,"Positive monetary purchase amount required");}
  }
  private void creator(String operation) { CoreFinancePolicy.actor(CoreOrderService.roles(),operation); }
  private Model find(Model company,String id) {
    Model purchase=one(CoreOrderService.DB+"CcmPurchase","self.company = ?1 AND self.functionalId = ?2",company,id);
    if(purchase==null)throw new CoreFault(404,"Purchase not found in current company");return purchase;
  }
  private void compute(Model nativeOrder) {
    // Native header compute consumes priceDiscounted; the native line compute
    // initializes it and the line tax/company amounts. Do not synthesize totals.
    Object lineService=service("com.axelor.apps.purchase.service.PurchaseOrderLineService");
    for(Model line:(List<Model>)get(nativeOrder,"purchaseOrderLineList"))call(lineService,"compute",line,nativeOrder);
    call(service("com.axelor.apps.purchase.service.PurchaseOrderService"),"computePurchaseOrder",nativeOrder);
  }
  private Model currency(String code) {
    if(!Set.of("USD","VES").contains(code))throw new CoreFault(422,"Unsupported fixture currency");
    Model currency=one("com.axelor.apps.base.db.Currency","self.codeISO = ?1",code);
    if(currency==null)throw new CoreFault(422,"Native currency unavailable");return currency;
  }
  private Model line(Model nativeOrder,BigDecimal value,Model tax,String label,BigDecimal discount) {
    Model line=create(PURCHASE+"PurchaseOrderLine");set(line,"purchaseOrder",nativeOrder);set(line,"productName",label);
    set(line,"unit",one("com.axelor.apps.base.db.Unit","self.name = ?1","CCM-LAB-UNIT"));
    set(line,"qty",BigDecimal.ONE);set(line,"price",value);set(line,"inTaxPrice",value);
    set(line,"discountAmount",discount);set(line,"discountTypeSelect",discount.signum()==0?0:2);
    set(line,"taxLineSet",new HashSet<>(List.of(tax)));return line;
  }
  private void lines(Model nativeOrder,JsonNode input) {
    BigDecimal value=amount(input);Model company=(Model)get(nativeOrder,"company");Model tax=NativeFinance.tax(company,BigDecimal.ZERO);
    List<Model> lines=new ArrayList<>();
    if(input.has("charges")) {
      JsonNode charges=input.get("charges");
      if(charges.size()!=3)throw new CoreFault(422,"LAB purchase charges require tax/freight/discount");
      BigDecimal taxAmount=new BigDecimal(charges.get(0).asText()),freight=new BigDecimal(charges.get(1).asText()),discount=new BigDecimal(charges.get(2).asText()).negate();
      if(taxAmount.signum()<0 || freight.signum()<0 || discount.signum()<0 || discount.compareTo(freight)>0)throw new CoreFault(422,"Invalid purchase charges");
      Model configured=one("com.axelor.apps.account.db.Tax","self.code = ?1","CCM-PO07-TAX");
      if(configured==null)throw new IllegalStateException("Native purchase tax configuration must commit first");
      tax=(Model)get(configured,"activeTaxLine");
      lines.add(line(nativeOrder,value,tax,"Synthetic purchase goods",BigDecimal.ZERO));
      lines.add(line(nativeOrder,freight,NativeFinance.tax(company,BigDecimal.ZERO),"Synthetic freight / fixed discount",discount));
    } else lines.add(line(nativeOrder,value,tax,"Synthetic purchase goods",BigDecimal.ZERO));
    // Retain Hibernate's managed orphan-removal collection through revisions.
    ((List<Model>)get(nativeOrder,"purchaseOrderLineList")).clear();
    for(Model line:lines)call(nativeOrder,"addPurchaseOrderLineListItem",line);
    save(nativeOrder);compute(nativeOrder);
  }
  private BigDecimal base(Model nativeOrder) {
    Model currency=(Model)get(nativeOrder,"currency"), company=(Model)get(nativeOrder,"company");
    if(get(currency,"codeISO").equals("VES")) {
      Model quote=one("com.axelor.apps.base.db.CurrencyConversionLine",
          "self.startCurrency = ?1 AND self.endCurrency = ?2 AND self.fromDate = ?3 AND self.toDate = ?3",
          get(company,"currency"),currency,DATE);
      if(quote==null)throw new CoreFault(422,"Exact purchase request-date native rate required");
    }
    BigDecimal result=(BigDecimal)call(service("com.axelor.apps.base.service.CurrencyService"),"getAmountCurrencyConvertedAtDate",
        currency,get(company,"currency"),get(nativeOrder,"inTaxTotal"),DATE);
    return MoneyPolicy.money(result);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> createPurchase(JsonNode input) {
    Model company=CoreOrderService.company(input);creator("purchase.create");JPA.em().refresh(company,LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"purchase.create",input);if(replay!=null)return replay;
    String id=id(input);amount(input);
    if(one(CoreOrderService.DB+"CcmPurchase","self.company = ?1 AND self.functionalId = ?2",company,id)!=null)throw new CoreFault(409,"Purchase functional ID exists");
    Model supplier=one("com.axelor.apps.base.db.Partner","self.partnerSeq = ?1","CCM-LAB-SUPPLIER-PARTNER");
    if(supplier==null)throw new IllegalStateException("Native supplier must commit first");
    Model nativeOrder=(Model)call(service("com.axelor.apps.purchase.service.PurchaseOrderCreateService"),"createPurchaseOrder",
        AuthUtils.getUser(),company,null,currency(input.path("currency").asText("USD")),DATE,null,"CCM-"+id,DATE,null,supplier,null);
    set(nativeOrder,"inAti",false);set(nativeOrder,"paymentMode",one("com.axelor.apps.account.db.PaymentMode","self.code = ?1","CCM-BANK"));
    set(nativeOrder,"paymentCondition",one("com.axelor.apps.account.db.PaymentCondition","self.code = ?1","CCM-NET0"));
    set(nativeOrder,"externalReference","CCM-"+id);nativeOrder=save(nativeOrder);lines(nativeOrder,input);
    Model purchase=record(CoreOrderService.DB+"CcmPurchase","company",company,"functionalId",id,"creator",AuthUtils.getUser(),
        "purchaseOrder",nativeOrder,"usdBase",base(nativeOrder),"payload",CoreOrderService.encode(input));
    if(input.path("currency").asText("USD").equals("VES")) {
      Model rate=one("com.axelor.apps.base.db.CurrencyConversionLine","self.startCurrency = ?1 AND self.endCurrency = ?2 AND self.fromDate = ?3 AND self.toDate = ?3",get(company,"currency"),get(nativeOrder,"currency"),DATE);
      set(purchase,"requestRate",get(rate,"exchangeRate"));save(purchase);
    }
    Map<String,Object> result=view(purchase);
    CoreRecordSupport.audit(company,id,"purchase.created",Map.of(),result,"Synthetic purchase draft",CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"purchase.create",input,result);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> request(JsonNode input) {
    Model company=CoreOrderService.company(input);creator("purchase.request");Model purchase=find(company,id(input));JPA.em().refresh(purchase,LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"purchase.request",input);if(replay!=null)return replay;
    if(!get(purchase,"state").toString().equals("DRAFT"))throw new CoreFault(409,"Purchase request state conflict");
    Map<String,Object> before=view(purchase);Model nativeOrder=(Model)get(purchase,"purchaseOrder");compute(nativeOrder);
    call(service("com.axelor.apps.purchase.service.PurchaseOrderService"),"requestPurchaseOrder",nativeOrder);
    purchase=managed(purchase);setEnum(purchase,"state","PENDING");set(purchase,"usdBase",base(managed(nativeOrder)));save(purchase);
    Map<String,Object> result=view(purchase);CoreRecordSupport.audit(company,id(input),"purchase.requested",before,result,input.path("reason").asText(),CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"purchase.request",input,result);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> approve(JsonNode input) {
    Model company=CoreOrderService.company(input);Set<String> roles=CoreOrderService.roles();
    if(roles.stream().noneMatch(Set.of("buyer","manager","director")::contains))throw new CoreFault(403,"Purchase approval role required");
    Model purchase=find(company,id(input));JPA.em().refresh(purchase,LockModeType.PESSIMISTIC_WRITE);
    if(((Model)get(purchase,"creator")).getId().equals(AuthUtils.getUser().getId()))throw new CoreFault(403,"Purchase self-approval denied");
    String level=MoneyPolicy.purchaseLevel((BigDecimal)get(purchase,"usdBase"));
    if(level.equals("DIRECTOR")&&!roles.contains("director") || level.equals("MANAGER")&&!roles.contains("manager")&&!roles.contains("director"))throw new CoreFault(403,"Purchase threshold role denied");
    Map<String,Object> replay=CoreRecordSupport.replay(company,"purchase.approve",input);if(replay!=null)return replay;
    if(!get(purchase,"state").toString().equals("PENDING"))throw new CoreFault(409,"Purchase approval state conflict");
    Map<String,Object> before=view(purchase);Model nativeOrder=(Model)get(purchase,"purchaseOrder");
    call(service("com.axelor.apps.purchase.service.PurchaseOrderWorkflowService"),"validatePurchaseOrder",nativeOrder);
    nativeOrder=managed(nativeOrder);purchase=managed(purchase);
    setEnum(purchase,"state","APPROVED");set(purchase,"approvedBy",AuthUtils.getUser());set(purchase,"approvedAt",get(nativeOrder,"validationDateTime"));save(purchase);
    Map<String,Object> result=view(purchase);CoreRecordSupport.audit(company,id(input),"purchase.approved",before,result,input.path("reason").asText(),CoreRecordSupport.key(input),false);
    CoreRecordSupport.event(company,id(input),"purchase.approved",get(purchase,"decisionRevision").toString(),result);
    return CoreRecordSupport.remember(company,"purchase.approve",input,result);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> revise(JsonNode input) {
    Model company=CoreOrderService.company(input);creator("purchase.revise");Model purchase=find(company,id(input));JPA.em().refresh(purchase,LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"purchase.revise",input);if(replay!=null)return replay;amount(input);
    Map<String,Object> before=view(purchase);Model nativeOrder=(Model)get(purchase,"purchaseOrder");
    Object workflow=service("com.axelor.apps.purchase.service.PurchaseOrderWorkflowService");
    if(!Integer.valueOf(1).equals(get(nativeOrder,"statusSelect"))) {call(workflow,"cancelPurchaseOrder",nativeOrder);nativeOrder=managed(nativeOrder);call(workflow,"draftPurchaseOrder",nativeOrder);}
    nativeOrder=managed(nativeOrder);lines(nativeOrder,input);purchase=managed(purchase);
    setEnum(purchase,"state","DRAFT");set(purchase,"usdBase",base(nativeOrder));set(purchase,"approvedBy",null);set(purchase,"approvedAt",null);
    set(purchase,"decisionRevision",((Integer)get(purchase,"decisionRevision"))+1);set(purchase,"payload",CoreOrderService.encode(input));save(purchase);
    Map<String,Object> result=view(purchase);CoreRecordSupport.audit(company,id(input),"purchase.revised",before,result,input.path("reason").asText(),CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"purchase.revise",input,result);
  }
  public Map<String,Object> view(Model purchase) {
    Model nativeOrder=(Model)get(purchase,"purchaseOrder");Map<String,Object> result=new LinkedHashMap<>();
    result.put("id",get(purchase,"functionalId"));result.put("native_id",purchase.getId());result.put("native_purchase_id",nativeOrder.getId());
    result.put("company_id",get(get(purchase,"company"),"code"));result.put("native_company_id",((Model)get(purchase,"company")).getId());
    result.put("creator",get(get(purchase,"creator"),"code"));result.put("state",get(purchase,"state").toString());result.put("native_status",get(nativeOrder,"statusSelect"));
    result.put("usd_base",get(purchase,"usdBase").toString());result.put("native_gross",get(nativeOrder,"inTaxTotal").toString());
    result.put("native_tax",get(nativeOrder,"taxTotal").toString());result.put("currency",get(get(nativeOrder,"currency"),"codeISO"));
    result.put("request_date",get(nativeOrder,"orderDate").toString());result.put("request_rate",get(purchase,"requestRate"));result.put("decision_revision",get(purchase,"decisionRevision"));
    result.put("approved_by",get(purchase,"approvedBy")==null?null:get(get(purchase,"approvedBy"),"code"));result.put("approved_at",get(purchase,"approvedAt")==null?null:get(purchase,"approvedAt").toString());
    result.put("native_validated_by",get(nativeOrder,"validatedByUser")==null?null:get(get(nativeOrder,"validatedByUser"),"code"));
    List<Map<String,Object>> lines=new ArrayList<>();for(Model line:(List<Model>)get(nativeOrder,"purchaseOrderLineList"))
      lines.add(Map.of("id",line.getId(),"native_purchase_id",((Model)get(line,"purchaseOrder")).getId(),"qty",get(line,"qty").toString(),"price",get(line,"price").toString(),"discount",get(line,"discountAmount").toString(),"ex_tax",get(line,"exTaxTotal").toString(),"in_tax",get(line,"inTaxTotal").toString()));
    result.put("lines",lines);return result;
  }
}
