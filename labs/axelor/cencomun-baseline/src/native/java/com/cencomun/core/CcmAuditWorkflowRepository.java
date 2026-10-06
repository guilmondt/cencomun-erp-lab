package com.cencomun.core;

import com.cencomun.core.db.CcmAudit;
import com.cencomun.core.db.repo.CcmAuditRepository;

/** Supported repository binding; no upstream changes. */
public class CcmAuditWorkflowRepository extends CcmAuditRepository {
  @Override public CcmAudit save(CcmAudit entity) {
    CoreWriteScope.require();
    if (entity.getId() != null) throw new CoreFault(403,"Semantic audit is immutable");
    return super.save(entity);
  }
  @Override public void remove(CcmAudit entity) {
    throw new CoreFault(403,"Native workflow records cannot be deleted by generic CRUD");
  }
}
