package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import jakarta.persistence.LockModeType;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Cash snapshots derive from posted native journal lines, never a second ledger. */
public class CoreCashService {
  static final String ACCOUNT="com.axelor.apps.account.db.";
  static final String BASE="com.axelor.apps.base.db.";
  static final LocalDate DATE=LocalDate.of(2026,10,1);
  static final Map<String,String> ACCOUNTS=Map.of("USD","CASH","VES","CASH-VES","POS","POS","TRANSFER","TRANSFER");
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> seed() throws Exception {
    NativeIndependentController.fixtureAdmin();FixtureBundle.verify();
    Model company=one(BASE+"Company","self.code = ?1","CCM-LAB-001"),partner=one(BASE+"Partner","self.partnerSeq = ?1","C001");
    Model journal=one(ACCOUNT+"Journal","self.company = ?1 AND self.code = ?2",company,"CCM-CORE-CASH");
    if(journal==null)throw new IllegalStateException("Cash sequence/configuration must commit first");
    JsonNode fixture=FixtureBundle.json("cash.json");
    for(String channel:List.of("USD","VES","POS","TRANSFER")) {
      Model currency=one(BASE+"Currency","self.codeISO = ?1",channel.equals("VES")?"VES":"USD");int n=0;
      for(JsonNode input:fixture.path("source_movements").get(channel)) {
        String origin="CCM-CORE-CASH-"+channel+"-"+(++n);
        if(one(ACCOUNT+"Move","self.company = ?1 AND self.origin = ?2",company,origin)!=null)continue;
        BigDecimal amount=new BigDecimal(input.asText());
        Model move=(Model)call(service("com.axelor.apps.account.service.move.MoveCreateService"),"createMove",journal,company,currency,partner,
            DATE,DATE,null,null,2,6,origin,origin,null);
        Object creator=service("com.axelor.apps.account.service.moveline.MoveLineCreateService");
        Model cash=(Model)call(creator,"createMoveLine",move,partner,one(ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-"+ACCOUNTS.get(channel)),amount.abs(),amount.signum()>0,DATE,1,origin,"Synthetic shared Core cash source");
        Model offset=(Model)call(creator,"createMoveLine",move,partner,one(ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-OPENING"),amount.abs(),amount.signum()<0,DATE,2,origin,"Synthetic shared Core cash offset");
        call(move,"addMoveLineListItem",cash);call(move,"addMoveLineListItem",offset);move=save(move);
        call(service("com.axelor.apps.account.service.move.MoveValidateService"),"accounting",move);
      }
    }
    JsonNode pending=fixture.get("pending_invoice");
    if(one(ACCOUNT+"Invoice","self.company = ?1 AND self.externalReference = ?2",company,pending.path("id").asText())==null) {
      Object factory=Beans.get(Class.forName("com.cencomun.core.NativeFxInvoiceFactory"));
      Model invoice=(Model)call(factory,"create",company,partner,one(ACCOUNT+"PaymentMode","self.code = ?1","CCM-CASH"),
          one(ACCOUNT+"PaymentCondition","self.code = ?1","CCM-NET0"),get(company,"currency"),DATE,pending.get("id").asText());
      Model product=one(BASE+"Product","self.code = ?1","P002"),line=create(ACCOUNT+"InvoiceLine");
      set(line,"invoice",invoice);set(line,"product",product);set(line,"productName",get(product,"name"));set(line,"unit",get(product,"unit"));
      set(line,"qty",BigDecimal.ONE);set(line,"price",new BigDecimal(pending.get("gross").asText()));
      set(line,"account",one(ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-REVENUE"));
      set(line,"taxLineSet",new HashSet<>(List.of(NativeFinance.tax(company,BigDecimal.ZERO))));
      call(service("com.axelor.apps.account.service.invoice.InvoiceLineService"),"compute",invoice,line);
      call(invoice,"addInvoiceLineListItem",line);invoice=save(invoice);
      call(service("com.axelor.apps.account.service.invoice.InvoiceService"),"validateAndVentilate",invoice);
    }
    return source(company);
  }
  public static Map<String,Object> source(Model company) {
    Map<String,String> totals=new LinkedHashMap<>();List<Map<String,Object>> sources=new ArrayList<>();
    Model journal=one(ACCOUNT+"Journal","self.company = ?1 AND self.code = ?2",company,"CCM-CORE-CASH");
    for(String channel:List.of("USD","VES","POS","TRANSFER")) {
      Model account=one(ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-"+ACCOUNTS.get(channel));
      BigDecimal sum=BigDecimal.ZERO;List<Map<String,Object>> rows=new ArrayList<>();
      if(journal!=null)for(Model line:list(ACCOUNT+"MoveLine","self.move.company = ?1 AND self.move.journal = ?2 AND self.account = ?3 AND self.move.statusSelect = ?4",company,journal,account,3).stream().sorted(java.util.Comparator.comparing(Model::getId)).toList()) {
        BigDecimal debit=(BigDecimal)get(line,"debit"),credit=(BigDecimal)get(line,"credit"),value=((BigDecimal)get(line,"currencyAmount")).abs();
        if(debit.compareTo(credit)<0)value=value.negate();sum=sum.add(value);
        Model move=(Model)get(line,"move");rows.add(Map.of("id",line.getId(),"native_move_id",move.getId(),"account_id",account.getId(),"account",get(account,"code"),
            "currency",get(get(move,"currency"),"codeISO"),"native_currency_amount",value.toString(),"move",Beans.get(NativeGateService.class).exportMove(move)));
      }
      totals.put(channel,MoneyPolicy.money(sum).toPlainString());sources.add(Map.of("channel",channel,"lines",rows));
    }
    Model pending=one(ACCOUNT+"Invoice","self.company = ?1 AND self.externalReference = ?2",company,"CASH-PENDING");
    Map<String,Object> result=new LinkedHashMap<>();result.put("expected",totals);result.put("sources",sources);
    if(pending!=null)result.put("pending_invoice",Map.of("id",pending.getId(),"reference",get(pending,"externalReference"),"company_id",company.getId(),
        "status",get(pending,"statusSelect"),"gross",get(pending,"inTaxTotal").toString(),"remaining",get(pending,"amountRemaining").toString(),
        "paid",get(pending,"amountPaid").toString(),"payments",list(ACCOUNT+"InvoicePayment","self.invoice = ?1",pending).stream().map(Model::getId).toList(),
        "move",Beans.get(NativeGateService.class).exportMove((Model)get(pending,"move"))));
    return result;
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> prepare(JsonNode input) {
    Model company=CoreOrderService.company(input);CoreFinancePolicy.actor(CoreOrderService.roles(),"cash.prepare");
    JPA.em().refresh(company,LockModeType.PESSIMISTIC_WRITE);Map<String,Object> replay=CoreRecordSupport.replay(company,"cash.prepare",input);if(replay!=null)return replay;
    String id=input.path("id").asText();if(!id.matches("[A-Z0-9][A-Z0-9-]{0,79}"))throw new CoreFault(422,"Invalid cash closing ID");
    Model close=one(CoreOrderService.DB+"CcmCashClose","self.company = ?1 AND self.functionalId = ?2",company,id);
    if(close!=null&&get(close,"state").toString().equals("CONFIRMED"))throw new CoreFault(409,"Confirmed cash closing immutable");
    Map<String,Object> before=close==null?Map.of("exists",false):view(close),source=source(company);
    Map<String,String> expected=(Map<String,String>)source.get("expected"),observed=new LinkedHashMap<>(),differences=new LinkedHashMap<>();
    if(!input.path("observed").isObject() || input.path("observed").size()!=4)throw new CoreFault(422,"All four cash channels required");
    for(String channel:List.of("USD","VES","POS","TRANSFER")) {
      BigDecimal amount;
      try{amount=new BigDecimal(input.path("observed").path(channel).asText());if(amount.signum()<0||amount.stripTrailingZeros().scale()>2)throw new IllegalArgumentException();}
      catch(IllegalArgumentException error){throw new CoreFault(422,"Invalid observed cash amount");}
      observed.put(channel,MoneyPolicy.money(amount).toPlainString());differences.put(channel,MoneyPolicy.money(amount.subtract(new BigDecimal(expected.get(channel)))).toPlainString());
    }
    if(close==null)close=create(CoreOrderService.DB+"CcmCashClose");
    set(close,"company",company);set(close,"functionalId",id);set(close,"expectedAmounts",CoreOrderService.encode(expected));
    set(close,"observedAmounts",CoreOrderService.encode(observed));set(close,"differences",CoreOrderService.encode(differences));
    set(close,"sourceSnapshot",CoreOrderService.encode(source));set(close,"preparedBy",AuthUtils.getUser());set(close,"note",input.path("note").asText());close=save(close);
    Map<String,Object> result=view(close);CoreRecordSupport.audit(company,id,"cash.prepared",before,result,input.path("reason").asText(),CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"cash.prepare",input,result);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> confirm(JsonNode input) {
    Model company=CoreOrderService.company(input);if(!CoreOrderService.roles().contains("manager"))throw new CoreFault(403,"Manager cash confirmation required");
    Model close=one(CoreOrderService.DB+"CcmCashClose","self.company = ?1 AND self.functionalId = ?2",company,input.path("id").asText());
    if(close==null)throw new CoreFault(404,"Cash closing not found");JPA.em().refresh(close,LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"cash.confirm",input);if(replay!=null)return replay;
    if(get(close,"state").toString().equals("CONFIRMED"))throw new CoreFault(409,"Confirmed cash closing immutable");
    Map<String,Object> before=view(close);JsonNode differences=CoreOrderService.JSON.valueToTree(before.get("differences"));
    boolean nonzero=false;for(JsonNode value:differences)if(new BigDecimal(value.asText()).signum()!=0)nonzero=true;
    String note=input.path("note").asText(get(close,"note").toString());if(nonzero&&note.isBlank())throw new CoreFault(422,"Cash discrepancy justification required");
    setEnum(close,"state","CONFIRMED");set(close,"confirmedBy",AuthUtils.getUser());
    set(close,"confirmedAt",call(service("com.axelor.apps.base.service.app.AppBaseService"),"getTodayDateTime",company) instanceof java.time.ZonedDateTime dt?dt.toLocalDateTime():null);
    set(close,"note",note);save(close);Map<String,Object> result=view(close);
    CoreRecordSupport.audit(company,input.path("id").asText(),"cash.confirmed",before,result,note.isBlank()?"Synthetic closing matches native ledger":note,CoreRecordSupport.key(input),false);
    CoreRecordSupport.event(company,input.path("id").asText(),"cash.closing.confirmed","1",result,CoreRecordSupport.key(input),null);
    return CoreRecordSupport.remember(company,"cash.confirm",input,result);
  }
  public static Map<String,Object> view(Model close) {
    Map<String,Object> result=new LinkedHashMap<>();result.put("id",get(close,"functionalId"));result.put("native_id",close.getId());result.put("company_id",get(get(close,"company"),"code"));
    result.put("state",get(close,"state").toString());result.put("note",get(close,"note"));result.put("prepared_by",get(get(close,"preparedBy"),"code"));
    result.put("confirmed_by",get(close,"confirmedBy")==null?null:get(get(close,"confirmedBy"),"code"));result.put("confirmed_at",get(close,"confirmedAt")==null?null:get(close,"confirmedAt").toString());
    for(String field:List.of("expectedAmounts","observedAmounts","differences","sourceSnapshot"))try{result.put(field,CoreOrderService.JSON.readValue((String)get(close,field),Map.class));}catch(Exception e){throw new IllegalStateException("Invalid native cash snapshot",e);}
    result.put("differences",result.remove("differences"));return result;
  }
}
