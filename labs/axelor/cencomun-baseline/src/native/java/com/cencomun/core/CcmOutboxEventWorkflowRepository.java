package com.cencomun.core;

import com.cencomun.core.db.CcmOutboxEvent;
import com.cencomun.core.db.repo.CcmOutboxEventRepository;

/** Supported repository binding; no upstream changes. */
public class CcmOutboxEventWorkflowRepository extends CcmOutboxEventRepository {
  @Override public CcmOutboxEvent save(CcmOutboxEvent entity) {
    CoreWriteScope.require();
    return super.save(entity);
  }
  @Override public void remove(CcmOutboxEvent entity) {
    throw new CoreFault(403,"Native workflow records cannot be deleted by generic CRUD");
  }
}
