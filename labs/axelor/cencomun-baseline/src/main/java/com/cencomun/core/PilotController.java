package com.cencomun.core;
import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import java.math.BigDecimal;
import java.util.UUID;

/** Native view buttons call authenticated transactional services. No economic logic in XML. */
public class PilotController {
  public void defaults(ActionRequest request,ActionResponse response) {
    flags(request,response);response.setValue("reference","P-"+UUID.randomUUID().toString().toUpperCase());
    response.setValue("lineList",java.util.List.of());response.setValue("kind","CASH");response.setValue("channel","STORE");
    response.setValue("financed",BigDecimal.ZERO);response.setValue("shipping",BigDecimal.ZERO);
  }
  public void flags(ActionRequest q,ActionResponse r) {
    PilotService.enabled();r.setValue("$supervisor",com.axelor.auth.AuthUtils.hasRole(com.axelor.auth.AuthUtils.getUser(),"CCM Pilot Supervisor"));
  }
  public void line(ActionRequest q,ActionResponse r) {
    Beans.get(PilotService.class).previewLine(CoreOrderService.JSON.valueToTree(q.getContext())).forEach(r::setValue);
  }
  public void create(ActionRequest request,ActionResponse response) {
    result(Beans.get(PilotService.class).createSale(CoreOrderService.JSON.valueToTree(request.getContext())),response);
  }
  private void action(ActionRequest request,ActionResponse response,String action) throws Exception {
    Object id=request.getContext().get("id");if(!(id instanceof Number))throw new CoreFault(422,"Open a saved sale");
    result(Beans.get(PilotService.class).act(((Number)id).longValue(),action,
        (String)request.getContext().get("$guide"),(String)request.getContext().get("$reason")),response);
  }
  public void collect(ActionRequest q,ActionResponse r)throws Exception{action(q,r,"collect");}
  public void deliver(ActionRequest q,ActionResponse r)throws Exception{action(q,r,"deliver");}
  public void cancel(ActionRequest q,ActionResponse r)throws Exception{action(q,r,"cancel");}
  public void settle(ActionRequest q,ActionResponse r)throws Exception{action(q,r,"settle");}
  public void open(ActionRequest q,ActionResponse r){result(Beans.get(PilotService.class).open(),r);}
  public void preview(ActionRequest q,ActionResponse r) {
    r.setValue("$expected",Beans.get(PilotService.class).previewCash().get("expected"));
  }
  public void close(ActionRequest q,ActionResponse r) {
    Object value=q.getContext().get("$counted");
    if(value==null)throw new CoreFault(422,"Enter physically counted cash");
    result(Beans.get(PilotService.class).close(new BigDecimal(value.toString()),(String)q.getContext().get("$reason")),r);
  }
  private void result(Model record,ActionResponse response) {
    response.setValue("id",record.getId());response.setReload(true);
    response.setNotify("Operación registrada. Revise los documentos nativos vinculados.");
  }
}
