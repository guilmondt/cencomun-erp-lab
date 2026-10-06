package com.cencomun.core;
import com.cencomun.core.db.CcmPilotLine;
import com.cencomun.core.db.repo.CcmPilotLineRepository;
/** Server-side write boundary: UI/API generic CRUD never mutates the workflow. */
public class CcmPilotLineWorkflowRepository extends CcmPilotLineRepository {
  @Override public CcmPilotLine save(CcmPilotLine entity) {CoreWriteScope.require();return super.save(entity);}
  @Override public void remove(CcmPilotLine entity) {throw new CoreFault(403,"Pilot workflow cannot be deleted");}
}
