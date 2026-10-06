package com.cencomun.core;
import com.cencomun.core.db.CcmPurchase;
import com.cencomun.core.db.repo.CcmPurchaseRepository;
/** Supported repository binding; writes require authenticated workflow. */
public class CcmPurchaseWorkflowRepository extends CcmPurchaseRepository {
  @Override public CcmPurchase save(CcmPurchase entity) { CoreWriteScope.require();return super.save(entity); }
  @Override public void remove(CcmPurchase entity) { throw new CoreFault(403,"Workflow records cannot be deleted by CRUD"); }
}
