package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.inject.persist.Transactional;
import jakarta.persistence.LockModeType;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZonedDateTime;
import java.util.*;

/** Pilot-only UI workflows. Native ERP documents remain the economic source of truth. */
public class PilotService {
  static final String DB=CoreOrderService.DB, BASE="com.axelor.apps.base.db.", ACCOUNT="com.axelor.apps.account.db.";
  static final LocalDate DATE=LocalDate.of(2026,10,1);
  static void enabled() {
    if (!"1".equals(System.getenv("CCM_PILOT_LAB")) || !"1".equals(System.getenv("CCM_CORE_LAB")))
      throw new CoreFault(404,"Pilot disabled");
  }
  static Model actor(String action) {
    enabled();
    if(AuthUtils.getUser()==null)throw new CoreFault(401,"Authentication required");
    PilotPolicy.actor(AuthUtils.hasRole(AuthUtils.getUser(),"CCM Pilot Operator"),
        AuthUtils.hasRole(AuthUtils.getUser(),"CCM Pilot Supervisor"), action);
    Model company=(Model)get(AuthUtils.getUser(),"activeCompany");
    if(company==null || !"CCM-LAB-001".equals(get(company,"code")))throw new CoreFault(403,"Pilot company denied");
    JPA.em().refresh(company,LockModeType.PESSIMISTIC_WRITE);
    return company;
  }
  static Model session(Model company, boolean requireOpen) {
    Model session=one(DB+"CcmPilotSession","self.company = ?1 AND self.businessDate = ?2",company,DATE);
    if(session==null)throw new CoreFault(409,"Supervisor must open the laboratory cash session first");
    if(requireOpen && !"OPEN".equals(get(session,"state")))throw new CoreFault(409,"Cash session confirmed and immutable");
    return session;
  }
  @Transactional(rollbackOn=Exception.class)
  public Model open() {
    Model company=actor("open");
    Model found=one(DB+"CcmPilotSession","self.company = ?1 AND self.businessDate = ?2",company,DATE);
    if(found!=null)return found;
    return record(DB+"CcmPilotSession","company",company,"businessDate",DATE,"state","OPEN");
  }
  static BigDecimal number(JsonNode input,String name) {
    try {return new BigDecimal(input.path(name).asText());}
    catch(NumberFormatException e){throw new CoreFault(422,"Invalid number: "+name);}
  }
  static Model selected(JsonNode input,String name,String model) {
    long id=input.path(name).path("id").asLong(0);
    Model found=id<=0?null:one(model,"self.id = ?1",id);
    if(found==null)throw new CoreFault(422,"Select "+name);
    return found;
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> previewLine(JsonNode input) {
    Model company=actor("create"),product=selected(input,"product",BASE+"Product");
    Model profile=one(DB+"CcmProductProfile","self.company = ?1 AND self.product = ?2",company,product);
    if(profile==null)throw new CoreFault(403,"Product outside pilot catalog");
    return Map.of("price",PilotPolicy.catalogPrice((BigDecimal)get(product,"salePrice")),
        "warrantyQuantity",get(profile,"warrantyQuantity"),"warrantyUnit",get(profile,"warrantyUnit").toString());
  }
  @Transactional(rollbackOn=Exception.class)
  public Model createSale(JsonNode input) {
    Model company=actor("create"), cash=session(company,true);
    String reference=input.path("reference").asText();
    if(!reference.matches("P-[A-Z0-9-]{1,70}"))throw new CoreFault(422,"Pilot reference required");
    Model customer=selected(input,"customer",BASE+"Partner");
    if(!Boolean.TRUE.equals(get(customer,"isCustomer")) || !((Set<?>)get(customer,"companySet")).contains(company))
      throw new CoreFault(403,"Customer outside the pilot company");
    String kind=input.path("kind").asText(),channel=input.path("channel").asText();
    if(kind.equals("CASH")&&!channel.equals("STORE"))throw new CoreFault(422,"Cash pilot uses store collection");
    ObjectNode payload=CoreOrderService.JSON.createObjectNode();
    payload.put("id",reference).put("customer_id",(String)get(customer,"partnerSeq"))
        .put("channel",channel).put("currency","USD").put("tax_rate","0.10")
        .put("financed_amount",number(input,"financed").toPlainString()).put("shipping_expense",number(input,"shipping").toPlainString());
    var nativeLines=payload.putArray("lines");List<Model> lines=new ArrayList<>();Map<String,BigDecimal> costs=new LinkedHashMap<>();
    if(!input.path("lineList").isArray()||input.path("lineList").isEmpty())throw new CoreFault(422,"At least one product line required");
    Set<Long> unique=new HashSet<>();
    for(JsonNode row:input.path("lineList")) {
      Model product=selected(row,"product",BASE+"Product");
      if(!unique.add(product.getId()))throw new CoreFault(422,"Combine duplicate product lines");
      Model profile=one(DB+"CcmProductProfile","self.company = ?1 AND self.product = ?2",company,product);
      if(profile==null)throw new CoreFault(403,"Product outside pilot catalog");
      if(kind.equals("CASHEA")&&!Boolean.TRUE.equals(get(profile,"casheaEnabled")))throw new CoreFault(422,"Product not eligible for Cashea");
      BigDecimal qty=number(row,"qty"),price=PilotPolicy.catalogPrice((BigDecimal)get(product,"salePrice"));
      MoneyPolicy.quantity(qty);qty=qty.setScale(0,java.math.RoundingMode.UNNECESSARY);
      String code=(String)get(product,"code");costs.put(code,(BigDecimal)get(product,"costPrice"));
      nativeLines.addObject().put("product_id",code).put("qty",qty.toPlainString()).put("unit_price",price.toPlainString());
      Model line=create(DB+"CcmPilotLine");set(line,"product",product);set(line,"qty",qty);set(line,"price",price);
      set(line,"warrantyQuantity",get(profile,"warrantyQuantity"));set(line,"warrantyUnit",get(profile,"warrantyUnit").toString());lines.add(line);
    }
    CoreOrderPolicy.input(payload);
    Map<String,BigDecimal> calculation=MoneyPolicy.calculate(payload,costs);
    PilotPolicy.amounts(kind,calculation.get("gross"),number(input,"financed"),number(input,"shipping"),calculation);
    String hash=CoreOrderService.hash(CoreOrderService.JSON.createObjectNode().put("kind",kind).set("order",payload));
    Model prior=one(DB+"CcmPilotSale","self.company = ?1 AND self.reference = ?2",company,reference);
    if(prior!=null){if(!hash.equals(get(prior,"payloadHash")))throw new CoreFault(409,"Reference payload conflict");return prior;}
    Model warehouse=one("com.axelor.apps.stock.db.StockLocation","self.company = ?1 AND self.name = ?2",company,"WH-LAB-001-PILOT");
    // Reservations are Cencomun extension records, never a forged native stock status.
    for(Model line:lines) {
      Model stock=one("com.axelor.apps.stock.db.StockLocationLine","self.stockLocation = ?1 AND self.product = ?2",warehouse,get(line,"product"));
      BigDecimal available=stock==null?BigDecimal.ZERO:(BigDecimal)get(stock,"currentQty");
      for(Model reserved:list(DB+"CcmPilotLine","self.sale.company = ?1 AND self.product = ?2 AND self.sale.state = ?3",company,get(line,"product"),"RESERVED"))available=available.subtract((BigDecimal)get(reserved,"qty"));
      if(available.compareTo((BigDecimal)get(line,"qty"))<0)throw new CoreFault(422,"Insufficient unreserved pilot stock");
    }
    Model order=Beans.get(NativeGateService.class).quotation(new NativeGateService.Progress(),payload,warehouse,false);
    Model sale=record(DB+"CcmPilotSale","company",managed(company),"session",managed(cash),"reference",reference,"payloadHash",hash,
        "customer",managed(customer),"kind",kind,"channel",channel,"state","RESERVED",
        "gross",calculation.get("gross"),"financed",number(input,"financed"),"shipping",number(input,"shipping"),"initial",calculation.get("upfront"),
        "commission",kind.equals("CASH")?BigDecimal.ZERO:calculation.get("commission"),"transfer",kind.equals("CASH")?BigDecimal.ZERO:calculation.get("transfer"),
        "payload",payload.toString(),"saleOrder",order,"creator",AuthUtils.getUser());
    for(Model line:lines)call(sale,"addLineListItem",line);sale=save(sale);
    audit(company,sale,"created","UI reservation; native quotation remains finalized");return sale;
  }
  static Model sale(Model company,long id) {
    Model sale=one(DB+"CcmPilotSale","self.id = ?1 AND self.company = ?2",id,company);
    if(sale==null)throw new CoreFault(403,"Sale outside the active company");return sale;
  }
  @Transactional(rollbackOn=Exception.class)
  public Model act(long id,String action,String guide,String reason) throws Exception {
    Model company=actor(action),sale=sale(company,id);
    String state=(String)get(sale,"state");
    // Authenticated, immutable re-entry returns its durable result without posting again.
    if(action.equals("collect") && get(sale,"initialVoucher")!=null)return sale;
    if(action.equals("deliver") && Set.of("DELIVERED","PAID","SETTLED").contains(state)
        || action.equals("settle")&&state.equals("SETTLED") || action.equals("cancel")&&state.equals("CANCELLED"))return sale;
    session(company,action.equals("collect")||action.equals("cancel")&&get(sale,"initialVoucher")!=null);PilotPolicy.transition(state,action);
    ObjectNode payload=(ObjectNode)CoreOrderService.JSON.readTree((String)get(sale,"payload"));
    if(action.equals("cancel")) {
      if(reason==null||reason.isBlank())throw new CoreFault(422,"Cancellation reason required");
      if(get(sale,"initialVoucher")!=null) {
        Model refund=PilotPayments.receipt(sale,true);sale=managed(sale);set(sale,"refundVoucher",refund);
        PilotPayments.matchRefund(sale);
      }
      call(service("com.axelor.apps.sale.service.saleorder.status.SaleOrderWorkflowService"),"cancelSaleOrder",get(sale,"saleOrder"),null,reason);
      sale=managed(sale);set(sale,"state","CANCELLED");
      // The native quotation cancellation may classify a first-time customer as
      // prospect. Keep the explicitly configured pilot customer eligible to buy.
      Model customer=managed((Model)get(sale,"customer"));set(customer,"isCustomer",true);save(customer);
    } else if(action.equals("collect")) {
      Model receipt=PilotPayments.receipt(sale,false);sale=managed(sale);set(sale,"initialVoucher",receipt);save(sale);
      if(get(sale,"invoice")!=null)PilotPayments.applyToInvoice(sale);
      sale=managed(sale);if(state.equals("DELIVERED")&&"CASH".equals(get(sale,"kind")))set(sale,"state","PAID");
    } else if(action.equals("deliver")) {
      if("WEB".equals(get(sale,"channel"))&&(guide==null||guide.isBlank()))throw new CoreFault(422,"Dispatch guide required");
      payload.put("guide",guide);
      call(service("com.axelor.apps.sale.service.saleorder.status.SaleOrderConfirmService"),"confirmSaleOrder",get(sale,"saleOrder"));
      sale=managed(sale);
      Map<String,Model> docs;
      try(PilotInvoiceTaxGuard.Scope taxScope=PilotInvoiceTaxGuard.enter(company,payload)) {
        docs=Beans.get(NativeGateService.class).deliver(new NativeGateService.Progress(),payload,(Model)get(sale,"saleOrder"));
      }
      company=managed(company);sale=managed(sale);
      Model cost=NativeFinance.postCost(company,managed((Model)get(sale,"customer")),docs.get("delivery"),payload);
      sale=managed(sale);set(sale,"delivery",managed(docs.get("delivery")));set(sale,"invoice",managed(docs.get("invoice")));
      set(sale,"costMove",managed(cost));set(sale,"guide",guide);save(sale);
      if(get(sale,"initialVoucher")!=null)PilotPayments.applyToInvoice(sale);
      sale=managed(sale);set(sale,"state","CASH".equals(get(sale,"kind"))&&get(sale,"initialVoucher")!=null?"PAID":"DELIVERED");
    } else if(action.equals("settle")) {
      if(!"CASHEA".equals(get(sale,"kind")))throw new CoreFault(409,"Only Cashea can be settled");
      if(((BigDecimal)get(sale,"initial")).signum()>0&&get(sale,"initialVoucher")==null)throw new CoreFault(409,"Initial payment has not been collected");
      Map<String,BigDecimal> amounts=Map.of("transfer",(BigDecimal)get(sale,"transfer"),"commission",(BigDecimal)get(sale,"commission"),"shipping",(BigDecimal)get(sale,"shipping"));
      Map<String,Object> result=NativeFinance.settleFinanced(company,(Model)get(sale,"customer"),(Model)get(sale,"invoice"),payload,amounts);
      sale=managed(sale);set(sale,"settlement",one(ACCOUNT+"Move","self.id = ?1",result.get("settlement_move_id")));set(sale,"state","SETTLED");
    }
    sale=save(sale);audit(managed(company),sale,action,reason==null||reason.isBlank()?"Pilot UI "+action:reason);return sale;
  }
  static void audit(Model company,Model sale,String action,String reason) {
    CoreRecordSupport.audit(managed(company),(String)get(sale,"reference"),"pilot."+action,Map.of(),Map.of("state",get(sale,"state"),"native_sale_order",((Model)get(sale,"saleOrder")).getId()),reason,"pilot:"+sale.getId()+":"+action,false);
  }
  /** Real posted CASH lines on initial-payment moves belonging to this session only. */
  static Map<String,Object> cashSource(Model company,Model session) {
    BigDecimal expected=BigDecimal.ZERO;List<Map<String,Object>> rows=new ArrayList<>();Set<Long> ids=new HashSet<>();
    for(Model sale:list(DB+"CcmPilotSale","self.company = ?1 AND self.session = ?2",company,session)) {
      for(String field:List.of("initialVoucher","refundVoucher")) {
        Model payment=(Model)get(sale,field);if(payment==null)continue;
        Model move=(Model)get(payment,"generatedMove");
        if(move==null||!Integer.valueOf(3).equals(get(move,"statusSelect"))||!company.equals(get(move,"company")))throw new CoreFault(409,"Receipt has no posted company move");
        if(!DATE.equals(get(payment,"paymentDate")))throw new CoreFault(409,"Payment date differs from cash session");
        for(Object line:(List<?>)get(move,"moveLineList")) {
          if(!"CCM-CASH".equals(get(get(line,"account"),"code")))continue;
          if(!ids.add(((Model)line).getId()))throw new CoreFault(409,"Duplicate cash source");
          BigDecimal amount=((BigDecimal)get(line,"debit")).subtract((BigDecimal)get(line,"credit"));expected=expected.add(amount);
          rows.add(Map.of("sale",sale.getId(),"voucher",payment.getId(),"kind",field,"move",move.getId(),"line",((Model)line).getId(),"amount",amount.toPlainString()));
        }
      }
    }
    return Map.of("expected",MoneyPolicy.money(expected),"sources",rows,"date",DATE.toString(),"session",session.getId());
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> previewCash() {
    Model company=actor("close"),cash=session(company,false);
    return cashSource(company,cash);
  }
  @Transactional(rollbackOn=Exception.class)
  public Model close(BigDecimal counted,String reason) {
    Model company=actor("close"),session=session(company,false);
    if("CONFIRMED".equals(get(session,"state"))) {
      if(((BigDecimal)get(session,"counted")).compareTo(counted)!=0 || !Objects.equals(get(session,"reason"),reason))
        throw new CoreFault(409,"Confirmed cash close immutable");return session;
    }
    Map<String,Object> source=cashSource(company,session);BigDecimal expected=(BigDecimal)source.get("expected");
    set(session,"difference",PilotPolicy.difference(expected,counted,reason));set(session,"expected",expected);set(session,"counted",counted);
    set(session,"reason",reason);set(session,"sourceSnapshot",CoreOrderService.encode(source));set(session,"state","CONFIRMED");
    set(session,"confirmedBy",AuthUtils.getUser());set(session,"confirmedAt",java.time.LocalDateTime.now());return save(session);
  }
}
