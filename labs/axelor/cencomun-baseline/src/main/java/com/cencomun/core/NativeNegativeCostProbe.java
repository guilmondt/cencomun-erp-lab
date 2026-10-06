package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.time.LocalDate;

/** Actual native receipt attempt, always rolled back; acceptance is a failure, not a rejection. */
public class NativeNegativeCostProbe {
  public static final class Progress {
    public String stage="native-fixture-read";
    public final java.util.Map<String,Object> evidence=new java.util.LinkedHashMap<>();
  }
  public static final class NativeAcceptedCost extends RuntimeException {
    public final java.util.Map<String,Object> evidence;
    NativeAcceptedCost(java.util.Map<String,Object> evidence) {
      super("Native receipt accepted and realized; diagnostic rollback only");this.evidence=evidence;
    }
  }
  @Transactional(rollbackOn = Exception.class)
  public void execute(String id, BigDecimal cost, Progress progress) {
    NativeIndependentController.fixtureAdmin();
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    Model warehouse=one("com.axelor.apps.stock.db.StockLocation","self.name = ?1","WH-LAB-001-"+id);
    Model source=one("com.axelor.apps.stock.db.StockLocation","self.name = ?1","CCM-LAB-SUPPLIER");
    Model product=one("com.axelor.apps.base.db.Product","self.code = ?1","P001");
    if(company==null || warehouse==null || source==null || product==null || get(product,"unit")==null)
      throw new IllegalStateException("Native cost probe fixture incomplete");
    progress.evidence.put("input_cost",cost.toPlainString());progress.evidence.put("qty","1");
    progress.evidence.put("company_id",company.getId());progress.evidence.put("warehouse_id",warehouse.getId());
    progress.evidence.put("product_id",product.getId());progress.stage="native-stock-move-create";
    Object stock=service("com.axelor.apps.stock.service.StockMoveService");
    Model move=(Model)call(stock,"createStockMove",null,null,company,source,warehouse,
        LocalDate.of(2026,10,1),LocalDate.of(2026,10,1),"Synthetic native cost control",3);
    progress.stage="native-stock-line-create";
    Model line=(Model)call(service("com.axelor.apps.stock.service.StockMoveLineService"),"createStockMoveLine",
        product,get(product,"name"),"Negative native cost probe",BigDecimal.ONE,cost,
        cost,get(product,"unit"),move,2,false,BigDecimal.ZERO,source,warehouse);
    set(line,"realQty",BigDecimal.ONE);call(move,"addStockMoveLineListItem",line);move=save(move);
    progress.evidence.put("native_move_id",move.getId());
    progress.stage="native-stock-move-plan";call(stock,"plan",move);move=managed(move);
    progress.evidence.put("planned_status",get(move,"statusSelect"));
    progress.stage="native-stock-move-realize";call(stock,"realize",move);move=managed(move);
    com.axelor.db.JPA.em().flush();Long nativeId=move.getId();com.axelor.db.JPA.em().clear();
    move=com.axelor.db.JPA.find(type("com.axelor.apps.stock.db.StockMove"),nativeId);
    progress.evidence.put("reloaded_status",get(move,"statusSelect"));
    progress.evidence.put("reloaded_lines",((java.util.List<Model>)get(move,"stockMoveLineList")).stream()
        .map(l->java.util.Map.of("id",l.getId(),"qty",get(l,"realQty").toString(),
            "unit_cost",get(l,"unitPriceUntaxed").toString(),"native_move_id",((Model)get(l,"stockMove")).getId())).toList());
    progress.stage="native-stock-realized-and-reloaded";
    throw new NativeAcceptedCost(new java.util.LinkedHashMap<>(progress.evidence));
  }
}
