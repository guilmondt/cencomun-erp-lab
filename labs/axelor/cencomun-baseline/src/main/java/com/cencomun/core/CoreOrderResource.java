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

/** Internal LAB actions; does not expand the shared six-operation adapter/MCP contract. */
@Path("/ccm/lab/orders")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class CoreOrderResource {
  @POST @Path("create")
  public Response create(JsonNode input) { return invoke(input, true); }
  @POST @Path("transition")
  public Response transition(JsonNode input) { return invoke(input, false); }
  private Response invoke(JsonNode input, boolean create) {
    CoreOrderService service = Beans.get(CoreOrderService.class);
    try {
      Map<String,Object> result = create ? service.createOrder(input) : service.transition(input);
      return Response.status(create && !Boolean.TRUE.equals(result.get("replayed")) ? 201 : 200).entity(result).build();
    } catch (Exception error) {
      Throwable root = error;
      while (root.getCause() != null && root.getCause() != root) root = root.getCause();
      int status = root instanceof CoreFault fault ? fault.status
          : root.getClass().getName().equals("com.axelor.apps.base.AxelorException") ? 422 : 500;
      String message = String.valueOf(root.getMessage());
      if (message.length() > 1800) message = message.substring(0,1800);
      // The intercepted economic transaction has already rolled back before this separate unit of work.
      service.rejected(input, message);
      Map<String,Object> body = new LinkedHashMap<>(); body.put("error_type",root.getClass().getName());
      body.put("error",message); body.put("native_stack",Arrays.stream(root.getStackTrace())
          .filter(f -> f.getClassName().startsWith("com.axelor.") || f.getClassName().startsWith("com.cencomun."))
          .limit(12).map(StackTraceElement::toString).toList());
      return Response.status(status).entity(body).build();
    }
  }
}
