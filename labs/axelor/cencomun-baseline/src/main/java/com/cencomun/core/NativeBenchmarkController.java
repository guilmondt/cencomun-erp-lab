package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

/** The frozen benchmark catalog commits before its native stock receipt.
 * NEW orders are loaded and timed through authenticated HTTP, never DB writes.
 */
public class NativeBenchmarkController {
  private static final String BASE="com.axelor.apps.base.db.",STOCK="com.axelor.apps.stock.db.";
  public void prepare(ActionRequest request,ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();NativeGateService.Progress p=new NativeGateService.Progress();
    Beans.get(NativeGateService.class).prepare(p,"BENCH");
    response.setValue("core_result",Beans.get(NativeBenchmarkController.class).catalog());
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> catalog() throws Exception {
    NativeIndependentController.fixtureAdmin();FixtureBundle.verify();
    JsonNode spec=FixtureBundle.json("benchmark.json");Model company=one(BASE+"Company","self.code = ?1","CCM-LAB-001"),usd=(Model)get(company,"currency"),unit=one(BASE+"Unit","self.name = ?1","CCM-LAB-UNIT");
    if(!list(BASE+"Product","self.code LIKE ?1","BENCH-P%").isEmpty())throw new IllegalStateException("Benchmark requires fresh isolated catalog");
    for(JsonNode f:spec.get("products")) {
      Model product=record(BASE+"Product","code",f.get("id").asText(),"name",f.get("name").asText(),"unit",unit,
          "salePrice",new BigDecimal(f.get("price").asText()),"purchasePrice",new BigDecimal(f.get("cost").asText()),"costPrice",new BigDecimal(f.get("cost").asText()),
          "stockManaged",true,"costTypeSelect",3,"productTypeSelect","storable","saleCurrency",usd,"purchaseCurrency",usd);
      Model profile=create(NativeIndependentController.PROFILE);set(profile,"company",company);set(profile,"product",product);
      set(profile,"marketplaceEnabled",true);set(profile,"casheaEnabled",true);set(profile,"casheaPrice",new BigDecimal(f.get("price").asText()));
      set(profile,"supplierReference",f.get("id").asText());set(profile,"warrantyQuantity",0);setEnum(profile,"warrantyUnit","DAY");setEnum(profile,"condition","NEW");save(profile);
    }
    for(JsonNode f:spec.get("customers"))record(BASE+"Partner","partnerSeq",f.get("id").asText(),"name",f.get("name").asText(),"isCustomer",true,"partnerTypeSelect",2,"currency",usd,"companySet",new HashSet<>(List.of(company)));
    return Map.of("products",spec.get("products").size(),"customers",spec.get("customers").size(),"fixture_sha256",FixtureBundle.sha(FixtureBundle.bytes("benchmark.json")));
  }
  public void seed(ActionRequest request,ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();response.setValue("core_result",Beans.get(NativeBenchmarkController.class).receipt());
  }
  @Transactional(rollbackOn=Exception.class)
  public Map<String,Object> receipt() throws Exception {
    NativeIndependentController.fixtureAdmin();Model company=one(BASE+"Company","self.code = ?1","CCM-LAB-001"),supplier=one(STOCK+"StockLocation","self.name = ?1","CCM-LAB-SUPPLIER"),warehouse=one(STOCK+"StockLocation","self.name = ?1","WH-LAB-001-BENCH"),unit=one(BASE+"Unit","self.name = ?1","CCM-LAB-UNIT");
    if(!list(STOCK+"StockLocationLine","self.stockLocation = ?1",warehouse).isEmpty())throw new IllegalStateException("Benchmark receipt already exists");
    Object stock=service("com.axelor.apps.stock.service.StockMoveService"),lines=service("com.axelor.apps.stock.service.StockMoveLineService");LocalDate date=LocalDate.of(2026,10,1);
    Model move=(Model)call(stock,"createStockMove",null,null,company,supplier,warehouse,date,date,"CCM benchmark frozen stock",3);
    for(JsonNode f:FixtureBundle.json("benchmark.json").get("products")) {
      Model product=one(BASE+"Product","self.code = ?1",f.get("id").asText());BigDecimal qty=new BigDecimal(f.get("stock").asText()),cost=new BigDecimal(f.get("cost").asText());
      Model line=(Model)call(lines,"createStockMoveLine",product,get(product,"name"),"Frozen benchmark stock",qty,cost,cost,unit,move,2,false,BigDecimal.ZERO,supplier,warehouse);
      set(line,"realQty",qty);call(move,"addStockMoveLineListItem",line);
    }
    move=save(move);call(stock,"plan",move);move=managed(move);call(stock,"realize",move);move=managed(move);
    return Map.of("native_stock_move_id",move.getId(),"native_status",get(move,"statusSelect"),"warehouse","WH-LAB-001-BENCH");
  }
  public void inspect(ActionRequest request,ActionResponse response) {
    NativeIndependentController.fixtureAdmin();Model company=one(BASE+"Company","self.code = ?1","CCM-LAB-001"),warehouse=one(STOCK+"StockLocation","self.name = ?1","WH-LAB-001-BENCH");
    response.setValue("core_result",Map.of("products",list(BASE+"Product","self.code LIKE ?1","BENCH-P%").stream().map(p->Map.of("id",p.getId(),"code",get(p,"code"),"name",get(p,"name"),"price",get(p,"salePrice"),"cost",get(p,"costPrice"))).toList(),
        "customers",list(BASE+"Partner","self.partnerSeq LIKE ?1","BENCH-C%").stream().map(c->Map.of("id",c.getId(),"code",get(c,"partnerSeq"),"name",get(c,"name"),"company_ids",((java.util.Set<Model>)get(c,"companySet")).stream().map(Model::getId).toList())).toList(),
        "stock",list(STOCK+"StockLocationLine","self.stockLocation = ?1",warehouse).stream().map(s->Map.of("id",s.getId(),"product",get(get(s,"product"),"code"),"qty",get(s,"currentQty"),"cost",get(s,"avgPrice"))).toList(),
        "orders",list(CoreOrderService.DB+"CcmOrder","self.company = ?1 AND self.functionalId LIKE ?2",company,"BENCH-%").stream().map(o->Beans.get(CoreOrderService.class).view(o)).toList(),
        "bank_rows",list(CoreOrderService.DB+"CcmBankRow","self.company = ?1",company).stream().filter(r->get(get(r,"statementLine"),"reference").toString().startsWith("BENCH-B")).map(CoreBankService::view).toList(),
        "company_id",company.getId(),"warehouse","WH-LAB-001-BENCH","read_boundary","separate-http-after-benchmark-commit"));
  }
}
