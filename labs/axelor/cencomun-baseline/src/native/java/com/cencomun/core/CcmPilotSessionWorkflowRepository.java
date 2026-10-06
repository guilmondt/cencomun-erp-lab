package com.cencomun.core;
import com.cencomun.core.db.CcmPilotSession;
import com.cencomun.core.db.repo.CcmPilotSessionRepository;
/** Server-side write boundary: UI/API generic CRUD never mutates the workflow. */
public class CcmPilotSessionWorkflowRepository extends CcmPilotSessionRepository {
  @Override public CcmPilotSession save(CcmPilotSession entity) {CoreWriteScope.require();return super.save(entity);}
  @Override public void remove(CcmPilotSession entity) {throw new CoreFault(403,"Pilot workflow cannot be deleted");}
}
