package com.cencomun.core;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;

/** Explicit laboratory restrictions, independent of the frozen Core contract. */
public final class PilotPolicy {
  public static BigDecimal catalogPrice(BigDecimal value) {
    MoneyPolicy.positiveMoney(value);
    return value.setScale(2,java.math.RoundingMode.UNNECESSARY);
  }
  public static void actor(boolean operator, boolean supervisor, String action) {
    if (!Set.of("create","collect","deliver","cancel","settle","open","close").contains(action))
      throw new CoreFault(422,"Unknown pilot action");
    if (!(supervisor || operator && Set.of("create","collect","deliver").contains(action)))
      throw new CoreFault(403,"Pilot role denied: " + action);
  }
  public static void transition(String state, String action) {
    boolean valid = switch(action) {
      case "collect" -> Set.of("RESERVED","DELIVERED").contains(state);
      case "deliver", "cancel" -> state.equals("RESERVED");
      case "settle" -> state.equals("DELIVERED");
      default -> false;
    };
    if (!valid) throw new CoreFault(409,"Pilot transition denied: " + state + " / " + action);
  }
  public static void amounts(String kind, BigDecimal gross, BigDecimal financed,
      BigDecimal shipping, Map<String,BigDecimal> calculation) {
    if (!Set.of("CASH","CASHEA").contains(kind)) throw new CoreFault(422,"Unknown payment kind");
    if (kind.equals("CASH") && (financed.signum()!=0 || shipping.signum()!=0))
      throw new CoreFault(422,"Cash pilot supports store collection only");
    if (kind.equals("CASHEA") && (financed.signum()<=0 || calculation.get("transfer").signum()<0))
      throw new CoreFault(422,"Cashea requires positive financing and nonnegative net transfer");
  }
  public static BigDecimal difference(BigDecimal expected, BigDecimal counted, String reason) {
    if (counted == null || counted.signum()<0 || counted.stripTrailingZeros().scale()>2)
      throw new CoreFault(422,"Counted cash must be nonnegative with at most two decimals");
    BigDecimal difference=MoneyPolicy.money(counted.subtract(expected));
    if (difference.signum()!=0 && (reason==null || reason.isBlank()))
      throw new CoreFault(422,"Explain the cash difference before confirming");
    return difference;
  }
  private PilotPolicy() {}
}
