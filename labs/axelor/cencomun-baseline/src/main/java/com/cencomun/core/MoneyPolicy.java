package com.cencomun.core;

import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.Map;

/** LAB-ONLY-v1 deterministic rules. Accounting and physical stock remain native. */
public final class MoneyPolicy {
  private static final BigDecimal ZERO = new BigDecimal("0.00");
  public static BigDecimal money(BigDecimal x) { return x.setScale(2, RoundingMode.HALF_UP); }
  public static BigDecimal decimal(String value) { return new BigDecimal(value); }
  public static void positiveMoney(BigDecimal value) {
    if (value.signum() <= 0 || value.stripTrailingZeros().scale() > 2)
      throw new IllegalArgumentException("Positive money with at most two decimals required");
  }
  public static void quantity(BigDecimal value) {
    if (value.signum() <= 0 || value.stripTrailingZeros().scale() > 0)
      throw new IllegalArgumentException("Positive integer quantity required");
  }
  public static void cost(BigDecimal value) {
    if (value.signum() < 0) throw new IllegalArgumentException("Negative cost forbidden");
  }
  public static BigDecimal convertLine(BigDecimal amount, BigDecimal rate) {
    if (rate.signum() <= 0 || rate.stripTrailingZeros().scale() > 6)
      throw new IllegalArgumentException("Invalid rate");
    return money(amount.multiply(rate));
  }
  public static String purchaseLevel(BigDecimal usd) {
    positiveMoney(usd);
    return usd.compareTo(new BigDecimal("200.00")) <= 0 ? "BUYER"
        : usd.compareTo(new BigDecimal("1000.00")) <= 0 ? "MANAGER" : "DIRECTOR";
  }
  public static Map<String, BigDecimal> calculate(JsonNode order, Map<String, BigDecimal> nativeCosts) {
    String channel = order.get("channel").asText();
    if (!channel.equals("STORE") && !channel.equals("WEB")) throw new IllegalArgumentException("Invalid channel");
    BigDecimal gross = ZERO, revenue = ZERO, costs = ZERO;
    BigDecimal rate = decimal(order.get("tax_rate").asText());
    if (rate.signum() < 0 || rate.stripTrailingZeros().scale() > 6) throw new IllegalArgumentException("Invalid tax");
    for (JsonNode line : order.get("lines")) {
      BigDecimal qty = decimal(line.get("qty").asText()); quantity(qty);
      BigDecimal price = decimal(line.get("unit_price").asText()); positiveMoney(price);
      BigDecimal c = nativeCosts.get(line.get("product_id").asText());
      if (c == null) throw new IllegalArgumentException("Missing native cost"); cost(c);
      BigDecimal lineGross = money(qty.multiply(price));
      gross = gross.add(lineGross);
      revenue = revenue.add(money(lineGross.divide(BigDecimal.ONE.add(rate), 16, RoundingMode.HALF_UP)));
      costs = costs.add(money(qty.multiply(c)));
    }
    BigDecimal financed = decimal(order.get("financed_amount").asText());
    if (financed.signum() < 0 || financed.compareTo(gross) > 0 || financed.stripTrailingZeros().scale() > 2)
      throw new IllegalArgumentException("Invalid financed amount");
    BigDecimal shipping = decimal(order.get("shipping_expense").asText());
    if (shipping.signum() < 0 || shipping.stripTrailingZeros().scale() > 2
        || (channel.equals("STORE") && shipping.signum() != 0)) throw new IllegalArgumentException("Invalid shipping");
    BigDecimal commission = money(gross.multiply(new BigDecimal(channel.equals("STORE") ? "0.04" : "0.06")))
        .add(money(financed.multiply(new BigDecimal("0.04"))));
    Map<String, BigDecimal> result = new LinkedHashMap<>();
    result.put("gross", money(gross)); result.put("revenue", money(revenue));
    result.put("tax", money(gross.subtract(revenue))); result.put("commission", money(commission));
    result.put("shipping", money(shipping)); result.put("cost", money(costs));
    BigDecimal net = gross.subtract(commission).subtract(shipping);
    result.put("net", money(net)); result.put("indicator", money(net.subtract(costs)));
    result.put("accounting_profit", money(revenue.subtract(commission).subtract(shipping).subtract(costs)));
    result.put("upfront", money(gross.subtract(financed)));
    result.put("transfer", money(financed.subtract(commission).subtract(shipping)));
    return result;
  }
  private MoneyPolicy() {}
}
