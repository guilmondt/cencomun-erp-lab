package com.cencomun.core;
import com.cencomun.core.db.CcmBankImport;
import com.cencomun.core.db.repo.CcmBankImportRepository;
/** Supported repository binding; writes require authenticated workflow. */
public class CcmBankImportWorkflowRepository extends CcmBankImportRepository {
  @Override public CcmBankImport save(CcmBankImport entity) { CoreWriteScope.require();return super.save(entity); }
  @Override public void remove(CcmBankImport entity) { throw new CoreFault(403,"Workflow records cannot be deleted by CRUD"); }
}
