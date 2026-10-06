package com.cencomun.core;
import com.cencomun.core.db.CcmCashClose;
import com.cencomun.core.db.repo.CcmCashCloseRepository;
/** Supported repository binding; writes require authenticated workflow. */
public class CcmCashCloseWorkflowRepository extends CcmCashCloseRepository {
  @Override public CcmCashClose save(CcmCashClose entity) { CoreWriteScope.require();return super.save(entity); }
  @Override public void remove(CcmCashClose entity) { throw new CoreFault(403,"Workflow records cannot be deleted by CRUD"); }
}
