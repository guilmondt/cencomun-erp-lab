package com.cencomun.core;
import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthService;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.util.*;

/** Explicit disposable pilot fixture, separate from every frozen Core scenario. */
public class PilotFixture {
  static void allowed() {
    PilotService.enabled();NativeIndependentController.fixtureAdmin();
    if(!"1".equals(System.getenv("CCM_PILOT_EPHEMERAL")))throw new CoreFault(403,"Automatic users are allowed only in the disposable pilot");
  }
  public void prepare(ActionRequest q,ActionResponse r)throws Exception {
    allowed();NativeGateService flow=Beans.get(NativeGateService.class);NativeGateService.Progress p=new NativeGateService.Progress();
    flow.activate(p);flow.prepare(p,"PILOT");
    Beans.get(PilotFixture.class).catalog();r.setNotify("Catálogo del piloto preparado");
  }
  @Transactional(rollbackOn=Exception.class)
  public void catalog() {
    allowed();Model company=one(PilotService.BASE+"Company","self.code = ?1","CCM-LAB-001");
    Model unit=one(PilotService.BASE+"Unit","self.name = ?1","CCM-LAB-UNIT");
    for(int i=1;i<=10;i++) {
      String code=String.format("P%03d",i);Model product=one(PilotService.BASE+"Product","self.code = ?1",code);
      if(product==null) {
        BigDecimal price=BigDecimal.valueOf(i*10L),cost=BigDecimal.valueOf(i*5L);
        product=record(PilotService.BASE+"Product","code",code,"name","Producto ficticio "+i,"unit",unit,"salePrice",price,"purchasePrice",cost,"costPrice",cost,
            "stockManaged",true,"costTypeSelect",3,"productTypeSelect","storable","saleCurrency",get(company,"currency"),"purchaseCurrency",get(company,"currency"));
        record(PilotService.ACCOUNT+"AccountManagement","company",company,"typeSelect",1,"product",product,
            "saleAccount",one(PilotService.ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-REVENUE"),
            "purchaseAccount",one(PilotService.ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-COGS"));
      }
      if(one(PilotService.DB+"CcmProductProfile","self.company = ?1 AND self.product = ?2",company,product)==null) {
        Model profile=create(PilotService.DB+"CcmProductProfile");set(profile,"company",company);set(profile,"product",product);
        set(profile,"casheaEnabled",i!=3);set(profile,"marketplaceEnabled",true);set(profile,"casheaPrice",PilotPolicy.catalogPrice((BigDecimal)get(product,"salePrice")));
        set(profile,"supplierReference","LAB-"+code);set(profile,"warrantyQuantity",i==3?0:i==2?6:i==4?90:i==5?1:12);setEnum(profile,"warrantyUnit",i==4?"DAY":i==5?"YEAR":"MONTH");setEnum(profile,"condition",i==2?"REFURBISHED":i==3?"USED":"NEW");save(profile);
      }
    }
    Model cash=one(PilotService.ACCOUNT+"Journal","self.company = ?1 AND self.code = ?2",company,"CCM-CASH");
    set(cash,"excessPaymentOk",true);save(cash); // Explicit native unapplied receipts in pilot only.
    if(one(PilotService.ACCOUNT+"PaymentMode","self.code = ?1","CCM-PILOT-REFUND")==null) {
      Model mode=record(PilotService.ACCOUNT+"PaymentMode","name","Pilot actual cash refund","code","CCM-PILOT-REFUND","typeSelect",5,"inOutSelect",2,
          "accountingMethodSelect",1,"accountingTriggerSelect",1,"moveAccountingDateSelect",1);
      record(PilotService.ACCOUNT+"AccountManagement","company",company,"typeSelect",3,"paymentMode",mode,"journal",cash,
          "cashAccount",one(PilotService.ACCOUNT+"Account","self.company = ?1 AND self.code = ?2",company,"CCM-CASH"));
    }
    for(String roleName:List.of("Operator","Supervisor")) {
      String name="CCM Pilot "+roleName;
      Model role=one("com.axelor.auth.db.Role","self.name = ?1",name);if(role==null)role=record("com.axelor.auth.db.Role","name",name);
      Set<Model> permissions=new HashSet<>();
      Map<String,String> scoped=new LinkedHashMap<>();
      for(String model:List.of("CcmPilotSale","CcmPilotSession","CcmProductProfile"))scoped.put(PilotService.DB+model,"self.company.id = ?");
      scoped.put(PilotService.BASE+"Product","EXISTS (SELECT p FROM CcmProductProfile p WHERE p.product = self AND p.company.id = ?)");
      scoped.put(PilotService.BASE+"Partner",NativeIndependentController.PARTNER_CONDITION);
      scoped.put("com.axelor.apps.stock.db.StockLocationLine","self.stockLocation.company.id = ?");
      scoped.put("com.axelor.apps.stock.db.StockLocation","self.company.id = ?");
      scoped.put("com.axelor.apps.sale.db.SaleOrder","self.company.id = ?");
      scoped.put("com.axelor.apps.stock.db.StockMove","self.company.id = ?");
      for(String model:List.of("Invoice","Move"))scoped.put(PilotService.ACCOUNT+model,"self.company.id = ?");
      scoped.put(PilotService.DB+"CcmPilotLine","self.sale.company.id = ?");
      scoped.put(PilotService.ACCOUNT+"PaymentVoucher","self.company.id = ?");
      scoped.put(PilotService.ACCOUNT+"InvoicePayment","self.invoice.company.id = ?");
      for(var entry:scoped.entrySet()) {
        String permissionName="pilot.read."+entry.getKey();
        Model permission=one("com.axelor.auth.db.Permission","self.name = ?1",permissionName);
        if(permission==null)permission=record("com.axelor.auth.db.Permission","name",permissionName,"object",entry.getKey(),"canRead",true,"canWrite",entry.getKey().contains("CcmPilot"),"canCreate",entry.getKey().contains("CcmPilot"),"canRemove",false,
            "condition",entry.getValue(),"conditionParams","__user__.activeCompany.id");permissions.add(permission);
      }
      set(role,"permissions",permissions);
      Set<Model> menus=new HashSet<>(list("com.axelor.meta.db.MetaMenu","self.name like ?1","ccm-pilot%"));
      if(menus.size()!=5)throw new CoreFault(409,"The five pilot menus must be installed before grants");
      set(role,"menus",menus);save(role);
      for(Model menu:menus){Set<Model> roles=new HashSet<>((Set<Model>)get(menu,"roles"));roles.add(role);set(menu,"roles",roles);save(menu);}
      String userCode="pilot-"+roleName.toLowerCase();Model user=one("com.axelor.auth.db.User","self.code = ?1",userCode);
      if(user==null) {
        String password=System.getenv("CCM_PILOT_"+roleName.toUpperCase()+"_PASSWORD");
        if(password==null||password.length()<20)throw new CoreFault(422,"Private disposable password configuration missing");
        user=record("com.axelor.auth.db.User","code",userCode,"name",name,"password",AuthService.getInstance().encrypt(password),"email",userCode+"@example.invalid");
      }
      set(user,"roles",new HashSet<>(List.of(role)));set(user,"blocked",false);set(user,"language","en");set(user,"activeCompany",company);set(user,"companySet",new HashSet<>(List.of(company)));save(user);
    }
  }
  public void seed(ActionRequest q,ActionResponse r) {allowed();Beans.get(PilotFixture.class).stock();r.setNotify("Existencias iniciales del piloto registradas");}
  @Transactional(rollbackOn=Exception.class)
  public void stock() {
    allowed();Model company=one(PilotService.BASE+"Company","self.code = ?1","CCM-LAB-001");
    com.axelor.db.JPA.em().refresh(company,jakarta.persistence.LockModeType.PESSIMISTIC_WRITE);
    Model warehouse=one("com.axelor.apps.stock.db.StockLocation","self.company = ?1 AND self.name = ?2",company,"WH-LAB-001-PILOT");
    if(!list("com.axelor.apps.stock.db.StockMove","self.toStockLocation = ?1",warehouse).isEmpty())return;
    Model supplier=one("com.axelor.apps.stock.db.StockLocation","self.name = ?1","CCM-LAB-SUPPLIER");
    Object stock=service("com.axelor.apps.stock.service.StockMoveService");
    Model move=(Model)call(stock,"createStockMove",null,null,company,supplier,warehouse,PilotService.DATE,PilotService.DATE,"CCM PILOT opening",3);
    for(Model profile:list(PilotService.DB+"CcmProductProfile","self.company = ?1",company)) {
      Model product=(Model)get(profile,"product");BigDecimal cost=(BigDecimal)get(product,"costPrice");
      Model line=(Model)call(service("com.axelor.apps.stock.service.StockMoveLineService"),"createStockMoveLine",product,get(product,"name"),"Pilot fixture receipt",new BigDecimal("20"),cost,cost,get(product,"unit"),move,2,false,BigDecimal.ZERO,supplier,warehouse);
      set(line,"realQty",new BigDecimal("20"));call(move,"addStockMoveLineListItem",line);
    }
    move=save(move);call(stock,"plan",move);call(stock,"realize",managed(move));
    NativeFinance.opening(managed(company),one(PilotService.BASE+"Partner","self.partnerSeq = ?1","C001"),managed(warehouse),"PILOT");
  }
}
