package com.cencomun.core;

import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/** Internal grouped finance acceptance API; critical roles are checked before replay. */
@Path("/ccm/lab/finance")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class CoreFinanceResource {
  @POST @Path("purchase/create") public Response create(JsonNode input){return invoke(input,"purchase.create");}
  @POST @Path("purchase/request") public Response request(JsonNode input){return invoke(input,"purchase.request");}
  @POST @Path("purchase/approve") public Response approve(JsonNode input){return invoke(input,"purchase.approve");}
  @POST @Path("purchase/revise") public Response revise(JsonNode input){return invoke(input,"purchase.revise");}
  @POST @Path("cash/prepare") public Response prepare(JsonNode input){return invoke(input,"cash.prepare");}
  @POST @Path("cash/confirm") public Response confirm(JsonNode input){return invoke(input,"cash.confirm");}
  @POST @Path("bank/import") public Response importBank(JsonNode input){return invoke(input,"bank.import");}
  @POST @Path("bank/reconcile") public Response reconcile(JsonNode input){return invoke(input,"bank.reconcile");}
  private Response invoke(JsonNode input,String operation) {
    try {
      Map<String,Object> result=switch(operation) {
        case "purchase.create"->Beans.get(CorePurchaseService.class).createPurchase(input);
        case "purchase.request"->Beans.get(CorePurchaseService.class).request(input);
        case "purchase.approve"->Beans.get(CorePurchaseService.class).approve(input);
        case "purchase.revise"->Beans.get(CorePurchaseService.class).revise(input);
        case "cash.prepare"->Beans.get(CoreCashService.class).prepare(input);
        case "cash.confirm"->Beans.get(CoreCashService.class).confirm(input);
        case "bank.import"->Beans.get(CoreBankService.class).importCsv(input);
        case "bank.reconcile"->Beans.get(CoreBankService.class).reconcile(input);
        default->throw new IllegalArgumentException(operation);
      };
      return Response.status(operation.equals("purchase.create")&&!Boolean.TRUE.equals(result.get("replayed"))?201:200).entity(result).build();
    }catch(Exception error) {
      Throwable root=error;while(root.getCause()!=null&&root.getCause()!=root)root=root.getCause();
      int status=root instanceof CoreFault f?f.status:root.getClass().getName().equals("com.axelor.apps.base.AxelorException")?422:root instanceof IllegalArgumentException?422:500;
      String message=String.valueOf(root.getMessage());if(message.length()>1800)message=message.substring(0,1800);
      Beans.get(CoreFinanceInspection.class).rejected(input,message);
      Map<String,Object> result=new LinkedHashMap<>();result.put("error_type",root.getClass().getName());result.put("error",message);
      result.put("native_stack",Arrays.stream(root.getStackTrace()).filter(f->f.getClassName().startsWith("com.axelor.")||f.getClassName().startsWith("com.cencomun.")).limit(18).map(StackTraceElement::toString).toList());
      return Response.status(status).entity(result).build();
    }
  }
}
