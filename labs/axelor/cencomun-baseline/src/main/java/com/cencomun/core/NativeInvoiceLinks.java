package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Read the pinned generator's actual source FK chain; never repair/write links. */
final class NativeInvoiceLinks {
  static Map<String, Object> inspect(Model invoice) {
    Model header = (Model) get(invoice, "saleOrder");
    List<Map<String, Object>> lines = new ArrayList<>();
    for (Object item : (List<?>) get(invoice, "invoiceLineList")) {
      Model source = (Model) get(item, "saleOrderLine");
      if (source == null) continue;
      Model order = (Model) get(source, "saleOrder");
      if (order == null) throw new IllegalStateException("Native invoice source line has no sale order");
      Model product = (Model) get(item, "product");
      Model parent = (Model) get(item, "invoice");
      lines.add(Map.of("invoice_line_id", ((Model) item).getId(), "sale_order_line_id", source.getId(),
          "sale_order_id", order.getId(), "sale_order_reference", get(order, "externalReference"),
          "sale_order_company_id", ((Model) get(order, "company")).getId(), "product_code", get(product, "code"),
          "parent_invoice_id", parent == null ? 0L : parent.getId()));
    }
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("native_invoice_id", invoice.getId());
    result.put("native_company_id", ((Model) get(invoice, "company")).getId());
    result.put("header_sale_order_id", header == null ? 0L : header.getId());
    result.put("header_sale_order_company_id", header == null ? 0L : ((Model) get(header, "company")).getId());
    result.put("header_sale_order_reference", header == null ? "" : get(header, "externalReference"));
    result.put("line_links", lines);
    result.put("source", "InvoiceLine.saleOrderLine.saleOrder");
    return result;
  }
}
