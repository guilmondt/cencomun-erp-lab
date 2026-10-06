package com.cencomun.core;

import com.cencomun.core.db.CcmOrder;
import com.cencomun.core.db.repo.CcmOrderRepository;

/** Supported repository binding; no upstream changes. */
public class CcmOrderWorkflowRepository extends CcmOrderRepository {
  @Override public CcmOrder save(CcmOrder entity) {
    CoreWriteScope.require();
    return super.save(entity);
  }
  @Override public void remove(CcmOrder entity) {
    throw new CoreFault(403,"Native workflow records cannot be deleted by generic CRUD");
  }
}
