package com.cencomun.core;

import com.cencomun.core.db.CcmOrderLine;
import com.cencomun.core.db.repo.CcmOrderLineRepository;

/** Supported repository binding; no upstream changes. */
public class CcmOrderLineWorkflowRepository extends CcmOrderLineRepository {
  @Override public CcmOrderLine save(CcmOrderLine entity) {
    CoreWriteScope.require();
    return super.save(entity);
  }
  @Override public void remove(CcmOrderLine entity) {
    throw new CoreFault(403,"Native workflow records cannot be deleted by generic CRUD");
  }
}
