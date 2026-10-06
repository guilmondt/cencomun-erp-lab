package com.cencomun.core;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.math.BigDecimal;
import java.util.Map;
class PilotPolicyTest {
  @Test void nativeScaleIsNormalizedWithoutRoundingInvalidPrices() {
    assertEquals(new BigDecimal("50.00"),PilotPolicy.catalogPrice(new BigDecimal("50.0000000000")));
    assertThrows(IllegalArgumentException.class,()->PilotPolicy.catalogPrice(new BigDecimal("50.001")));
  }
  @Test void operatorCannotSettleCancelOrConfirmCash() {
    for(String action:new String[]{"settle","cancel","open","close"})assertEquals(403,assertThrows(CoreFault.class,()->PilotPolicy.actor(true,false,action)).status);
    PilotPolicy.actor(true,false,"deliver");PilotPolicy.actor(false,true,"close");
    assertThrows(CoreFault.class,()->PilotPolicy.actor(false,false,"create"));
  }
  @Test void cancellationAndHandoverCannotFollowDelivery() {
    PilotPolicy.transition("RESERVED","cancel");
    for(String state:new String[]{"DELIVERED","SETTLED","PAID","CANCELLED"})assertThrows(CoreFault.class,()->PilotPolicy.transition(state,"cancel"));
    assertThrows(CoreFault.class,()->PilotPolicy.transition("RESERVED","settle"));
    PilotPolicy.transition("DELIVERED","settle");
  }
  @Test void countedDifferenceRequiresExplanationAndExactCents() {
    assertThrows(CoreFault.class,()->PilotPolicy.difference(new BigDecimal("100"),new BigDecimal("99"),""));
    assertEquals(new BigDecimal("-1.00"),PilotPolicy.difference(new BigDecimal("100"),new BigDecimal("99"),"Falta un dólar en conteo"));
    assertEquals(new BigDecimal("0.00"),PilotPolicy.difference(new BigDecimal("100"),new BigDecimal("100"),""));
    for(String bad:new String[]{"-1","0.001"})assertThrows(CoreFault.class,()->PilotPolicy.difference(BigDecimal.ZERO,new BigDecimal(bad),"note"));
  }
  @Test void cashCannotCreateFinancingOrShippingAndCasheaCannotTransferNegative() {
    assertThrows(CoreFault.class,()->PilotPolicy.amounts("CASH",BigDecimal.TEN,BigDecimal.ONE,BigDecimal.ZERO,Map.of()));
    assertThrows(CoreFault.class,()->PilotPolicy.amounts("CASHEA",BigDecimal.TEN,BigDecimal.ONE,BigDecimal.ZERO,Map.of("transfer",new BigDecimal("-0.01"))));
  }
}
