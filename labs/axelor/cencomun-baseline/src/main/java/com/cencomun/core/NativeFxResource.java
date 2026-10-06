package com.cencomun.core;

import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import java.util.Map;

/** LAB currency acceptance through authenticated native Axelor sessions. */
@Path("/ccm/lab/currency")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class NativeFxResource {
  @POST @Path("payment")
  public Map<String, Object> payment(JsonNode input) { return Beans.get(NativeFxService.class).convert(input); }
  @POST @Path("authorize")
  public Map<String, Object> authorize(JsonNode input) { return Beans.get(NativeFxService.class).authorize(input); }
}
