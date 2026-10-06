package com.cencomun.core;

import com.cencomun.core.db.CcmRequestKey;
import com.cencomun.core.db.repo.CcmRequestKeyRepository;

/** Supported repository binding; no upstream changes. */
public class CcmRequestKeyWorkflowRepository extends CcmRequestKeyRepository {
  @Override public CcmRequestKey save(CcmRequestKey entity) {
    CoreWriteScope.require();
    return super.save(entity);
  }
  @Override public void remove(CcmRequestKey entity) {
    throw new CoreFault(403,"Native workflow records cannot be deleted by generic CRUD");
  }
}
