package com.cencomun.core;

import com.cencomun.core.db.CcmAudit;
import com.cencomun.core.db.repo.CcmAuditRepository;

/** Supported repository binding; no upstream changes. */
public class CcmAuditWorkflowRepository extends CcmAuditRepository {
  @Override public CcmAudit save(CcmAudit entity) {
    if (entity.getId() != null) throw new jakarta.ws.rs.ForbiddenException("Semantic audit is immutable");
    CoreWriteScope.require();
    return super.save(entity);
  }
  @Override public void remove(CcmAudit entity) {
    throw new jakarta.ws.rs.ForbiddenException("Semantic audit cannot be deleted by generic CRUD");
  }
}
