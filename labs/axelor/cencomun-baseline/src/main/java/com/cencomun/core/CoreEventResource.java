package com.cencomun.core;

import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import java.util.Map;

@Path("/ccm/lab/events") @Consumes(MediaType.APPLICATION_JSON) @Produces(MediaType.APPLICATION_JSON)
public class CoreEventResource {
  @POST @Path("dispatch") public Map<String,Object> dispatch(JsonNode input){return Beans.get(CoreOutboxService.class).dispatch(input);}
}
