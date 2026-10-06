package com.cencomun.core;

import java.io.StringReader;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

/** The fixed host's Commons CSV parser preserves quoted cells and signed decimal text. */
public class NativeBankCsv {
  public List<Map<String,String>> parse(String csv) throws Exception {
    List<Map<String,String>> result=new ArrayList<>();
    try(CSVParser parser=CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build().parse(new StringReader(csv))) {
      if(!parser.getHeaderNames().equals(List.of("account","date","reference","currency","amount","description")))throw new IllegalArgumentException("Shared bank CSV header required");
      for(CSVRecord row:parser) {
        if(!row.isConsistent())throw new IllegalArgumentException("Inconsistent bank CSV record");
        result.add(new LinkedHashMap<>(row.toMap()));
      }
    }
    return result;
  }
}
