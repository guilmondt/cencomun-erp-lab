package com.cencomun.core;
import com.cencomun.core.db.CcmBankRow;
import com.cencomun.core.db.repo.CcmBankRowRepository;
/** Supported repository binding; writes require authenticated workflow. */
public class CcmBankRowWorkflowRepository extends CcmBankRowRepository {
  @Override public CcmBankRow save(CcmBankRow entity) { CoreWriteScope.require();return super.save(entity); }
  @Override public void remove(CcmBankRow entity) { throw new CoreFault(403,"Workflow records cannot be deleted by CRUD"); }
}
