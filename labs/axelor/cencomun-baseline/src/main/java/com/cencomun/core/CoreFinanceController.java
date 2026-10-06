package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

/** Versioned synthetic native configuration, committed before any sequence-consuming finance call. */
public class CoreFinanceController {
  public void prepare(ActionRequest request,ActionResponse response) {
    NativeIndependentController.fixtureAdmin();Object apps=service("com.axelor.studio.app.service.AppService");
    String scope=String.valueOf(request.getContext().get("case_id"));
    if(!List.of("PURCHASE","CASH","BANK").contains(scope))throw new IllegalArgumentException("Separate finance fixture scope required");
    for(String code:scope.equals("PURCHASE")?List.of("purchase"):scope.equals("BANK")?List.of("bank-payment"):List.<String>of()) {
      Model app=one("com.axelor.studio.db.App","self.code = ?1",code);
      if(app==null)throw new IllegalStateException("Fixed native App metadata missing: "+code);
      if(!Boolean.TRUE.equals(call(apps,"isApp",code)))call(apps,"installApp",app,"en");
    }
    response.setValue("core_result",Beans.get(CoreFinanceController.class).configure(scope));
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> configure(String scope) {
    NativeIndependentController.fixtureAdmin();Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    if(company==null)throw new IllegalStateException("Committed native catalog required");
    Map<String,Object> result=new java.util.LinkedHashMap<>();result.put("company_id",company.getId());result.put("fixture_scope",scope);
    if(scope.equals("PURCHASE")) {
    Model config=one("com.axelor.apps.purchase.db.PurchaseConfig","self.company = ?1",company);
    if(config==null){config=record("com.axelor.apps.purchase.db.PurchaseConfig","company",company);set(company,"purchaseConfig",config);save(company);}
    String sequenceCode;
    try { sequenceCode=(String)type("com.axelor.apps.base.db.repo.SequenceRepository").getField("PURCHASE_ORDER").get(null); }
    catch(ReflectiveOperationException error){throw new IllegalStateException("Pinned native purchase sequence constant missing",error);}
    Model seq=one("com.axelor.apps.base.db.Sequence","self.company = ?1 AND self.codeSelect = ?2",company,sequenceCode);
    if(seq==null) {
      seq=record("com.axelor.apps.base.db.Sequence","company",company,"name","Cencomun LAB purchase sequence","codeSelect",sequenceCode,"prefixe","CCM-PO-","padding",6,"toBeAdded",1);
      record("com.axelor.apps.base.db.SequenceVersion","sequence",seq,"startDate",LocalDate.of(2026,1,1),"endDate",LocalDate.of(2026,12,31),"nextNum",1L);
    }
    Model supplier=one("com.axelor.apps.base.db.Partner","self.partnerSeq = ?1","CCM-LAB-SUPPLIER-PARTNER");
    if(supplier==null)supplier=record("com.axelor.apps.base.db.Partner","partnerSeq","CCM-LAB-SUPPLIER-PARTNER","name","Synthetic Core supplier",
        "isSupplier",true,"partnerTypeSelect",2,"currency",get(company,"currency"),"companySet",new HashSet<>(List.of(company)));
    NativeFinance.configurePartner(company,supplier);
    Model tax=one("com.axelor.apps.account.db.Tax","self.code = ?1","CCM-PO07-TAX");
    if(tax==null) {
      Model zeroTax=one("com.axelor.apps.account.db.Tax","self.code = ?1","CCM-BASE");
      tax=record("com.axelor.apps.account.db.Tax","code","CCM-PO07-TAX","name","Synthetic PO07 tax from frozen charge15/base180","taxType",get(zeroTax,"taxType"));
      BigDecimal percentage=new BigDecimal("15.00").multiply(new BigDecimal("100")).divide(new BigDecimal("180.00"),6,RoundingMode.HALF_UP);
      Model taxLine=record("com.axelor.apps.account.db.TaxLine","tax",tax,"value",percentage,"startDate",LocalDate.of(2026,1,1),"endDate",LocalDate.of(2026,12,31));set(tax,"activeTaxLine",taxLine);save(tax);
    }
    result.put("native_purchase_config_id",config.getId());result.put("native_sequence_id",seq.getId());result.put("native_sequence_code",sequenceCode);result.put("native_supplier_id",supplier.getId());result.put("native_purchase_tax_id",tax.getId());
    }
    if(scope.equals("CASH")) {
    for(String category:List.of("CASH-VES","POS","TRANSFER"))
      if(one("com.axelor.apps.account.db.Account","self.company = ?1 AND self.code = ?2",company,"CCM-"+category)==null)NativeFinance.account(company,category,"cash",false);
    Model journal=one("com.axelor.apps.account.db.Journal","self.company = ?1 AND self.code = ?2",company,"CCM-CORE-CASH");
    if(journal==null)journal=NativeFinance.journal(company,"CORE-CASH",5);
    NativeFinance.journalAccounts(company,"CORE-CASH","CASH","CASH-VES","POS","TRANSFER","OPENING");
    result.put("native_cash_journal_id",journal.getId());
    }
    if(scope.equals("BANK")) {
    Model bankDetails=one("com.axelor.apps.base.db.BankDetails","self.code = ?1","BANK-USD-001");
    if(bankDetails==null) {
      Model bank=record("com.axelor.apps.base.db.Bank","name","Synthetic LAB bank","code","CCM-LAB-BANK","bic","LABOUS00XXX");
      bankDetails=record("com.axelor.apps.base.db.BankDetails","company",company,"partner",get(company,"partner"),"code","BANK-USD-001",
          "label","Synthetic account for shared Core fixture","ownerName","Synthetic LAB","bank",bank,"iban","GB82WEST12345698765432","currency",get(company,"currency"));
    }
    result.put("native_bank_details_id",bankDetails.getId());
    }
    result.put("scope","Synthetic LAB only; official create/workflow services unchanged");return result;
  }
  public void inspect(ActionRequest request,ActionResponse response) {
    NativeIndependentController.fixtureAdmin();String id=String.valueOf(request.getContext().get("case_id"));
    response.setValue("core_result",Beans.get(CoreFinanceInspection.class).inspect(id));
  }
  public void cashSeed(ActionRequest request,ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();response.setValue("core_result",Beans.get(CoreCashService.class).seed());
  }
}
