package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.time.LocalDate;

/** Actual native receipt attempt, always rolled back; acceptance is a failure, not a rejection. */
public class NativeNegativeCostProbe {
  public static final class NativeAcceptedNegativeCost extends RuntimeException {
    NativeAcceptedNegativeCost() { super("Pinned ERP accepted a negative-cost StockMoveLine and realized it; diagnostic rollback only"); }
  }
  @Transactional(rollbackOn = Exception.class)
  public void execute(String id) {
    NativeIndependentController.fixtureAdmin();
    Model company=one("com.axelor.apps.base.db.Company","self.code = ?1","CCM-LAB-001");
    Model warehouse=one("com.axelor.apps.stock.db.StockLocation","self.name = ?1","WH-LAB-001-"+id);
    Model source=one("com.axelor.apps.stock.db.StockLocation","self.name = ?1","CCM-LAB-SUPPLIER");
    Model product=one("com.axelor.apps.base.db.Product","self.code = ?1","P001");
    Object stock=service("com.axelor.apps.stock.service.StockMoveService");
    Model move=(Model)call(stock,"createStockMove",null,null,company,source,warehouse,
        LocalDate.of(2026,10,1),LocalDate.of(2026,10,1),"Synthetic negative native cost",3);
    Model line=(Model)call(service("com.axelor.apps.stock.service.StockMoveLineService"),"createStockMoveLine",
        product,get(product,"name"),"Negative native cost probe",BigDecimal.ONE,new BigDecimal("-0.01"),
        new BigDecimal("-0.01"),get(product,"unit"),move,2,false,BigDecimal.ZERO,source,warehouse);
    set(line,"realQty",BigDecimal.ONE);call(move,"addStockMoveLineListItem",line);move=save(move);
    call(stock,"plan",move);move=managed(move);call(stock,"realize",move);
    throw new NativeAcceptedNegativeCost();
  }
}
