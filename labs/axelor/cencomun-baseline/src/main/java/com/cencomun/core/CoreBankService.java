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
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Shared CSV adapter creates native statement lines and uses native reconciliation validation. */
public class CoreBankService {
  static final String BANK="com.axelor.apps.bankpayment.db.",ACCOUNT="com.axelor.apps.account.db.",BASE="com.axelor.apps.base.db.";
  static String hash(String value) {
    try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
    catch(Exception error){throw new IllegalStateException(error);}
  }
  static Model details(Model company,String code) {
    Model value=one(BASE+"BankDetails","self.company = ?1 AND self.code = ?2",company,code);
    if(value==null)throw new CoreFault(422,"Configured native LAB bank account required");return value;
  }
  static List<Model> book(Model company,String currency,BigDecimal amount,LocalDate day) {
    List<Model> candidates=new ArrayList<>();if(amount.signum()<=0)return candidates;
    Model mode=one(ACCOUNT+"PaymentMode","self.code = ?1","CCM-BOOK");
    if(mode!=null)for(Model voucher:list(ACCOUNT+"PaymentVoucher","self.company = ?1 AND self.paymentMode = ?2",company,mode)) {
      if(!Integer.valueOf(2).equals(get(voucher,"statusSelect"))||!currency.equals(get(get(voucher,"currency"),"codeISO")))continue;
      if(Math.abs(ChronoUnit.DAYS.between((LocalDate)get(voucher,"paymentDate"),day))>2)continue;
      Model move=(Model)get(voucher,"generatedMove");if(move==null||!Integer.valueOf(3).equals(get(move,"statusSelect")))continue;
      for(Model line:(List<Model>)get(move,"moveLineList"))
        if("CCM-BANK".equals(get(get(line,"account"),"code")) && ((BigDecimal)get(line,"debit")).subtract((BigDecimal)get(line,"credit")).compareTo(amount)==0
            && ((BigDecimal)get(line,"bankReconciledAmount")).signum()==0)candidates.add(line);
    }
    candidates.sort(java.util.Comparator.comparing(Model::getId));return candidates;
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> importCsv(JsonNode input) throws Exception {
    Model company=CoreOrderService.company(input);CoreFinancePolicy.actor(CoreOrderService.roles(),"bank.import");
    JPA.em().refresh(company,LockModeType.PESSIMISTIC_WRITE);
    String csv;try{csv=new String(Base64.getDecoder().decode(input.path("csv_base64").asText()),StandardCharsets.UTF_8);}catch(IllegalArgumentException error){throw new CoreFault(422,"Invalid bank CSV encoding");}
    if(csv.length()>2_000_000)throw new CoreFault(422,"LAB bank CSV too large");String account=input.path("account").asText();Model details=details(company,account);String fileHash=hash(csv);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"bank.import",input);if(replay!=null)return replay;
    Model prior=one(CoreOrderService.DB+"CcmBankImport","self.company = ?1 AND self.accountCode = ?2 AND self.fileHash = ?3",company,account,fileHash);
    if(prior!=null){Map<String,Object> result=CoreOrderService.JSON.readValue((String)get(prior,"result"),Map.class);result.put("replayed",true);return result;}
    List<Map<String,String>> rows=(List<Map<String,String>>)call(Beans.get(Class.forName("com.cencomun.core.NativeBankCsv")),"parse",csv);
    if(rows.isEmpty())throw new CoreFault(422,"Bank CSV records required");
    LocalDate first=LocalDate.MAX,last=LocalDate.MIN;
    for(Map<String,String> row:rows) {if(!account.equals(row.get("account")))throw new CoreFault(422,"Bank account mismatch");LocalDate date=LocalDate.parse(row.get("date"));if(date.isBefore(first))first=date;if(date.isAfter(last))last=date;}
    Model statement=record(BANK+"BankStatement","name","CCM-LAB-"+fileHash.substring(0,16),"fromDate",first,"toDate",last);
    int sequence=0,created=0,duplicates=0;List<Map<String,Object>> results=new ArrayList<>();
    for(Map<String,String> row:rows) {
      sequence++;LocalDate day=LocalDate.parse(row.get("date"));BigDecimal amount=new BigDecimal(row.get("amount"));
      if(amount.signum()==0||amount.stripTrailingZeros().scale()>2)throw new CoreFault(422,"Signed bank amount required to two decimals");
      String currencyCode=row.get("currency"),reference=row.get("reference");Model currency=one(BASE+"Currency","self.codeISO = ?1",currencyCode);
      if(currency==null||!currency.equals(get(details,"currency")))throw new CoreFault(422,"Bank account currency mismatch");
      String txHash=hash(CoreOrderService.encode(List.of(get(company,"code"),account,day.toString(),reference,currencyCode,MoneyPolicy.money(amount).toPlainString())));
      Model existing=one(CoreOrderService.DB+"CcmBankRow","self.company = ?1 AND self.accountCode = ?2 AND self.transactionHash = ?3",company,account,txHash);
      if(existing!=null){duplicates++;results.add(Map.of("classification","DUPLICATE","key",txHash));continue;}
      Model line=(Model)call(service("com.axelor.apps.bankpayment.service.bankstatementline.BankStatementLineCreationService"),"createBankStatementLine",
          statement,sequence,details,amount.signum()<0?amount.abs():BigDecimal.ZERO,amount.signum()>0?amount:BigDecimal.ZERO,currency,row.get("description"),day,day,null,null,"CCM-LAB",reference);
      line=save(line);List<Model> candidates=book(company,currencyCode,amount,day);
      List<Model> exact=new ArrayList<>();for(Model candidate:candidates)if(reference.equals(get(get(get(candidate,"move"),"paymentVoucher"),"ref"))&&day.equals(get(get(candidate,"move"),"date")))exact.add(candidate);
      String classification=exact.size()==1?"EXACT":candidates.isEmpty()?"UNMATCHED":candidates.size()==1?"PROBABLE":"AMBIGUOUS";
      Model core=record(CoreOrderService.DB+"CcmBankRow","company",company,"accountCode",account,"transactionHash",txHash,"classification",classification,
          "candidates",CoreOrderService.encode(candidates.stream().map(Model::getId).toList()),"statementLine",line);
      if(classification.equals("EXACT"))reconcileNative(core,exact.get(0),"Automatic unique exact reference/date/currency/amount");
      results.add(view(core));created++;
    }
    Map<String,Object> result=new LinkedHashMap<>();result.put("id",input.path("id").asText());result.put("rows",rows.size());result.put("created",created);result.put("duplicates",duplicates);result.put("results",results);result.put("native_statement_id",statement.getId());result.put("file_hash",fileHash);
    record(CoreOrderService.DB+"CcmBankImport","company",company,"accountCode",account,"fileHash",fileHash,"bankStatement",statement,"result",CoreOrderService.encode(result));
    CoreRecordSupport.audit(company,input.path("id").asText(),"bank.imported",Map.of(),result,input.path("reason").asText(),CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"bank.import",input,result);
  }
  static void reconcileNative(Model row,Model candidate,String reason) {
    Model company=(Model)get(row,"company"),line=(Model)get(row,"statementLine"),move=(Model)get(candidate,"move");
    if(!company.equals(get(move,"company")) || !Integer.valueOf(3).equals(get(move,"statusSelect")))throw new CoreFault(403,"Posted bank-book company mismatch");
    Model header=record(BANK+"BankReconciliation","name","CCM-LAB-"+row.getId(),"company",company,"currency",get(line,"currency"),"bankDetails",get(line,"bankDetails"),
        "cashAccount",get(candidate,"account"),"journal",get(move,"journal"),"fromDate",get(line,"operationDate"),"toDate",get(line,"operationDate"),"bankStatement",get(line,"bankStatement"),"comments",reason);
    Object service=service("com.axelor.apps.bankpayment.service.bankreconciliation.BankReconciliationLineService");
    Model nativeLine=(Model)call(service,"createBankReconciliationLine",line);set(nativeLine,"bankReconciliation",header);nativeLine=save(nativeLine);
    call(header,"addBankReconciliationLineListItem",nativeLine);save(header);
    call(service,"reconcileBRLAndMoveLine",nativeLine,candidate);
    call(service("com.axelor.apps.bankpayment.service.bankreconciliation.BankReconciliationValidateService"),"validate",header);
    row=managed(row);set(row,"bookLine",managed(candidate));set(row,"reconciliation",managed(header));save(row);
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> reconcile(JsonNode input) {
    Model company=CoreOrderService.company(input);if(!CoreOrderService.roles().contains("manager"))throw new CoreFault(403,"Manager bank reconciliation required");
    JPA.em().refresh(company,LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> replay=CoreRecordSupport.replay(company,"bank.reconcile",input);if(replay!=null)return replay;
    Model row=one(CoreOrderService.DB+"CcmBankRow","self.company = ?1 AND self.transactionHash = ?2",company,input.path("transaction_key").asText());if(row==null)throw new CoreFault(404,"Bank transaction not found");
    if(get(row,"reconciliation")!=null)throw new CoreFault(409,"Bank transaction already reconciled");
    String reason=input.path("reason").asText();if(reason.isBlank())throw new CoreFault(422,"Manual reconciliation justification required");
    Model candidate=JPA.find(type(ACCOUNT+"MoveLine"),input.path("candidate_id").asLong());if(candidate==null)throw new CoreFault(422,"Native bank-book candidate required");
    Model statementLine=(Model)get(row,"statementLine");BigDecimal amount=((BigDecimal)get(statementLine,"credit")).subtract((BigDecimal)get(statementLine,"debit"));
    List<Model> candidates=book(company,String.valueOf(get(get(statementLine,"currency"),"codeISO")),amount,(LocalDate)get(statementLine,"operationDate"));
    if(candidates.stream().noneMatch(c->c.getId().equals(candidate.getId())))throw new CoreFault(422,"Candidate is not an eligible native unreconciled book line");
    Map<String,Object> before=view(row);reconcileNative(row,candidate,reason);Map<String,Object> result=view(managed(row));
    CoreRecordSupport.audit(company,input.path("id").asText(),"bank.reconciled",before,result,reason,CoreRecordSupport.key(input),false);
    return CoreRecordSupport.remember(company,"bank.reconcile",input,result);
  }
  public static Map<String,Object> view(Model row) {
    Model line=(Model)get(row,"statementLine");Map<String,Object> result=new LinkedHashMap<>();
    result.put("id",row.getId());result.put("key",get(row,"transactionHash"));result.put("classification",get(row,"classification"));result.put("native_transaction_id",line.getId());
    try{result.put("candidates",CoreOrderService.JSON.readValue((String)get(row,"candidates"),List.class));}catch(Exception error){throw new IllegalStateException(error);}
    result.put("account",get(row,"accountCode"));result.put("date",get(line,"operationDate").toString());result.put("reference",get(line,"reference"));result.put("currency",get(get(line,"currency"),"codeISO"));
    for(String field:List.of("debit","credit","amountRemainToReconcile"))result.put(field,get(line,field).toString());
    result.put("native_statement_id",((Model)get(line,"bankStatement")).getId());result.put("native_bank_company_id",((Model)get(get(line,"bankDetails"),"company")).getId());
    Model reconcile=(Model)get(row,"reconciliation");result.put("reconciled",reconcile!=null);
    if(reconcile!=null) {
      Model book=(Model)get(row,"bookLine");result.put("book_line_id",book.getId());result.put("native_bank_reconciled_amount",get(book,"bankReconciledAmount").toString());
      result.put("statement_book_line_id",get(line,"moveLine")==null?null:((Model)get(line,"moveLine")).getId());
      result.put("native_book_reference",get(get(get(book,"move"),"paymentVoucher"),"ref"));
      result.put("reconciliation",Map.of("id",reconcile.getId(),"status",get(reconcile,"statusSelect"),"company_id",((Model)get(reconcile,"company")).getId(),
          "validated_by",get(get(reconcile,"validatedByUser"),"code"),"validated_at",get(reconcile,"validateDateTime").toString(),
          "lines",((List<Model>)get(reconcile,"bankReconciliationLineList")).stream().map(l->Map.of("id",l.getId(),"is_posted",get(l,"isPosted"),"statement_line_id",((Model)get(l,"bankStatementLine")).getId(),"book_line_id",((Model)get(l,"moveLine")).getId())).toList()));
    }
    return result;
  }
}
