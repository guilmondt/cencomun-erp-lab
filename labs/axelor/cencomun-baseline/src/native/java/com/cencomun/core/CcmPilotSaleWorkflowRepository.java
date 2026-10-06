package com.cencomun.core;
import com.cencomun.core.db.CcmPilotSale;
import com.cencomun.core.db.repo.CcmPilotSaleRepository;
/** Server-side write boundary: UI/API generic CRUD never mutates the workflow. */
public class CcmPilotSaleWorkflowRepository extends CcmPilotSaleRepository {
  @Override public CcmPilotSale save(CcmPilotSale entity) {CoreWriteScope.require();return super.save(entity);}
  @Override public void remove(CcmPilotSale entity) {throw new CoreFault(403,"Pilot workflow cannot be deleted");}
}
