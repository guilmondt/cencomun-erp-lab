package com.cencomun.core;

import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.MediaType;
import java.util.Map;

/** LAB currency acceptance through authenticated native Axelor sessions. */
@Path("/ccm/lab/currency")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class NativeFxResource {
  @POST @Path("payment")
  public Map<String, Object> payment(JsonNode input) {
    try { return Beans.get(NativeFxService.class).payment(input); }
    catch (WebApplicationException denied) { throw denied; }
    catch (Exception error) {
      Throwable root = error;
      while (root.getCause() != null && root.getCause() != root) root = root.getCause();
      throw new WebApplicationException(Response.status(500).entity(Map.of(
          "error_type", root.getClass().getName(), "error", String.valueOf(root.getMessage()),
          "native_stack", java.util.Arrays.stream(root.getStackTrace())
              .filter(f -> f.getClassName().startsWith("com.axelor.") || f.getClassName().startsWith("com.cencomun."))
              .limit(12).map(StackTraceElement::toString).toList())).build());
    }
  }
  @POST @Path("convert")
  public Map<String, Object> convert(JsonNode input) { return Beans.get(NativeFxService.class).convert(input); }
  @POST @Path("authorize")
  public Response authorize(JsonNode input) {
    try {return Response.ok(Beans.get(NativeFxService.class).authorize(input)).build();}
    catch(WebApplicationException error) {
      String reason=String.valueOf(error.getMessage());
      Beans.get(NativeFxService.class).rejectedAuthorization(input,reason);
      return Response.status(error.getResponse().getStatus()).entity(Map.of("error",reason,"error_type",error.getClass().getName())).build();
    }
  }
}
