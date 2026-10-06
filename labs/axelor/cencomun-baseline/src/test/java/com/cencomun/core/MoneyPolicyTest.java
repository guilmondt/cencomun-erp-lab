package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** These are server policy unit tests, explicitly separate from native coverage groups. */
public class MoneyPolicyTest {
  @Test void fixedFixturesAndRevisionTwoRemainByteIdentical() throws Exception { assertEquals(16, FixtureBundle.verify()); }
  @Test void allFourMoneyCasesMatchTheFixedOracleWithoutFeedingItIntoCalculations() throws Exception {
    Map<String, BigDecimal> costs = new LinkedHashMap<>();
    for (JsonNode product : FixtureBundle.json("products.json")) costs.put(product.get("id").asText(), new BigDecimal(product.get("cost").asText()));
    JsonNode oracle = FixtureBundle.json("oracle.json");
    for (JsonNode order : FixtureBundle.json("orders.json")) {
      Map<String, BigDecimal> result = MoneyPolicy.calculate(order, costs);
      for (Map.Entry<String, BigDecimal> entry : result.entrySet())
        assertEquals(0, entry.getValue().compareTo(new BigDecimal(oracle.get(order.get("id").asText()).get(entry.getKey()).asText())), order.get("id") + ": " + entry.getKey());
    }
  }
  @Test void quantitiesRejectZeroNegativeAndFractions() {
    for (String x : new String[]{"0", "-1", "0.5", "1.000001"}) assertThrows(IllegalArgumentException.class, () -> MoneyPolicy.quantity(new BigDecimal(x)));
    MoneyPolicy.quantity(new BigDecimal("2.00"));
  }
  @Test void pricesRejectInvalidPrecisionWithoutRoundingToAccept() {
    for (String x : new String[]{"0", "-1", "0.005"}) assertThrows(IllegalArgumentException.class, () -> MoneyPolicy.positiveMoney(new BigDecimal(x)));
  }
  @Test void negativeCostsAreRejected() { assertThrows(IllegalArgumentException.class, () -> MoneyPolicy.cost(new BigDecimal("-0.01"))); }
  @Test void exchangeConversionRoundsEachLine() {
    BigDecimal line = MoneyPolicy.convertLine(new BigDecimal("0.01"), new BigDecimal("41.000000"));
    assertEquals(new BigDecimal("0.82"), line.add(line));
    assertThrows(IllegalArgumentException.class, () -> MoneyPolicy.convertLine(line, BigDecimal.ZERO));
    assertThrows(IllegalArgumentException.class, () -> MoneyPolicy.convertLine(line, new BigDecimal("40.0000001")));
  }
  @Test void purchaseLimitsKeepAllSixExactBoundaries() {
    String[] amounts={"199.99","200.00","200.01","999.99","1000.00","1000.01"};
    String[] roles={"BUYER","BUYER","MANAGER","MANAGER","MANAGER","DIRECTOR"};
    for(int i=0;i<amounts.length;i++) assertEquals(roles[i], MoneyPolicy.purchaseLevel(new BigDecimal(amounts[i])));
  }
}
