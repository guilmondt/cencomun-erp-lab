package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** State/role policy regression; ERP acceptance remains actual authenticated CI. */
class CoreOrderPolicyTest {
  private void deny(int status, Runnable operation) { assertEquals(status,assertThrows(CoreFault.class,operation::run).status); }
  @Test void storeAndWebPathsRequireEveryStage() {
    String[] store={"NEW","REVIEWED","APPROVED","FULFILLED","SETTLED"};
    String[] web={"NEW","REVIEWED","APPROVED","PREPARING","SHIPPED","SETTLED"};
    for(int i=1;i<store.length;i++)CoreOrderPolicy.transition("STORE",store[i-1],store[i],null);
    for(int i=1;i<web.length;i++)CoreOrderPolicy.transition("WEB",web[i-1],web[i],"GUIDE-LAB-001");
  }
  @Test void unknownStatesCannotBecomeAnEnumOrEconomicAction() {
    for(String c: new String[]{"STORE","WEB"})deny(409,()->CoreOrderPolicy.transition(c,"NEW","UNKNOWN-LAB",null));
  }
  @Test void fivePhysicalAttemptsBeforeAcceptanceRejectWithoutRelaxingTheGraph() {
    for(String state:new String[]{"NEW","REVIEWED"}) {
      deny(409,()->CoreOrderPolicy.transition("STORE",state,"FULFILLED",null));
      deny(409,()->CoreOrderPolicy.transition("WEB",state,"SHIPPED","GUIDE-LAB-001"));
    }
    deny(409,()->CoreOrderPolicy.transition("WEB","APPROVED","SHIPPED","GUIDE-LAB-001"));
  }
  @Test void missingWebGuideIsInvalidAfterPreparing() { deny(422,()->CoreOrderPolicy.transition("WEB","PREPARING","SHIPPED",null)); }
  @Test void exceptionPathsDoNotAllowCancellationAfterHandover() {
    for(String channel:new String[]{"STORE","WEB"}) for(String state:new String[]{"NEW","REVIEWED"}) {
      CoreOrderPolicy.transition(channel,state,"REJECTED",null); CoreOrderPolicy.transition(channel,state,"CANCELLED",null);
    }
    CoreOrderPolicy.transition("STORE","APPROVED","CANCELLED",null);
    CoreOrderPolicy.transition("WEB","APPROVED","CANCELLED",null);
    CoreOrderPolicy.transition("WEB","PREPARING","CANCELLED",null);
    deny(409,()->CoreOrderPolicy.transition("STORE","FULFILLED","CANCELLED",null));
    deny(409,()->CoreOrderPolicy.transition("WEB","SHIPPED","CANCELLED",null));
  }
  @Test void authenticatedSimulatorAndOperatorHaveDifferentResponsibilities() {
    for(String target:new String[]{"REVIEWED","APPROVED","REJECTED","CANCELLED","SETTLED"}) {
      CoreOrderPolicy.actor(Set.of("simulator"),"transition",target);
      deny(403,()->CoreOrderPolicy.actor(Set.of("operator"),"transition",target));
      deny(403,()->CoreOrderPolicy.actor(Set.of("mcp"),"transition",target));
    }
    for(String target:new String[]{"PREPARING","FULFILLED","SHIPPED"}) {
      CoreOrderPolicy.actor(Set.of("operator"),"transition",target);
      deny(403,()->CoreOrderPolicy.actor(Set.of("simulator"),"transition",target));
    }
    CoreOrderPolicy.actor(Set.of("mcp"),"create","NEW"); deny(403,()->CoreOrderPolicy.actor(Set.of("reader"),"create","NEW"));
  }
  @Test void fixedPayloadsRemainValidWithoutChangingTheirValues() throws Exception {
    for(var input:FixtureBundle.json("orders.json"))CoreOrderPolicy.input(input);
  }
  @Test void invalidQuantityAndPriceMustRejectBeforeNativeDocumentCreation() throws Exception {
    for(String value:new String[]{"0","-1","0.5"}) {
      ObjectNode input=(ObjectNode)FixtureBundle.json("orders.json").get(0).deepCopy();
      ((ObjectNode)input.get("lines").get(0)).put("qty",value); deny(422,()->CoreOrderPolicy.input(input));
    }
    for(String value:new String[]{"0","-1","0.005"}) {
      ObjectNode input=(ObjectNode)FixtureBundle.json("orders.json").get(0).deepCopy();
      ((ObjectNode)input.get("lines").get(0)).put("unit_price",value); deny(422,()->CoreOrderPolicy.input(input));
    }
  }
  @Test void genericCrudDoesNotInheritWorkflowWriteCapability() { deny(403,CoreWriteScope::require); }
}
