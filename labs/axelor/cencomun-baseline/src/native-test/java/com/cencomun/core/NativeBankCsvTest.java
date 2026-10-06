package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class NativeBankCsvTest {
  private static final String HEADER="account,date,reference,currency,amount,description\r\n";
  @Test void preservesQuotedDescriptionSignedAmountsAndCrLf() throws Exception {
    var rows=new NativeBankCsv().parse(HEADER+"BANK-USD-001,2026-10-01,NEGATIVE-001,USD,-10.00,\"Synthetic, quoted description\"\r\n");
    assertEquals(1,rows.size());assertEquals(new BigDecimal("-10.00"),new BigDecimal(rows.getFirst().get("amount")));
    assertEquals("Synthetic, quoted description",rows.getFirst().get("description"));
  }
  @Test void refusesChangedSharedHeader() {
    assertThrows(IllegalArgumentException.class,()->new NativeBankCsv().parse(HEADER.replace("amount","total")));
  }
  @Test void refusesMalformedShortRow() {
    assertThrows(IllegalArgumentException.class,()->new NativeBankCsv().parse(HEADER+"BANK-USD-001,2026-10-01,REF,USD\r\n"));
  }
}
