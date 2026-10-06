package com.cencomun.core;

import com.axelor.auth.AuthUtils;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashMap;
import java.util.Map;

/** Test-only action, disabled unless the disposable CI runtime explicitly enables it. */
public class NativeGateController {
  private static void guard() {
    if (!"1".equals(System.getenv("CCM_CORE_LAB")) || AuthUtils.getUser() == null
        || !"admin".equals(AuthUtils.getUser().getCode()))
      throw new SecurityException("Core integration actions require the isolated LAB runtime administrator");
  }
  private String caseId(ActionRequest request) {
    String value = String.valueOf(request.getContext().get("case_id"));
    if (!value.equals("CO00") && !value.equals("TAX01-W")) throw new IllegalArgumentException("Gate case not allowed");
    return value;
  }
  public void execute(ActionRequest request, ActionResponse response) {
    guard();
    String id = caseId(request);
    NativeGateService.Progress progress = new NativeGateService.Progress();
    Map<String, Object> result = new LinkedHashMap<>(); result.put("case", id);
    result.put("reference", FixtureBundle.REFERENCE); result.put("actor", AuthUtils.getUser().getCode());
    NativeGateService nativeService = Beans.get(NativeGateService.class);
    try {
      result.put("verified_files", FixtureBundle.verify());
      JsonNode input = null;
      for (JsonNode order : FixtureBundle.json("orders.json")) if (order.get("id").asText().equals(id)) input = order;
      if (input == null) throw new IllegalArgumentException("Case absent from fixed fixtures");
      nativeService.activate(progress); nativeService.seed(progress, id); nativeService.sell(progress, input);
      result.put("status", "PASS");
    } catch (Exception error) {
      Throwable root = error;
      while (root.getCause() != null && root.getCause() != root) root = root.getCause();
      boolean implementationFailure = root instanceof IllegalStateException
          || root instanceof IllegalArgumentException || root instanceof ClassCastException;
      result.put("status", implementationFailure ? "FAIL" : "BLOCKED"); result.put("failed_stage", progress.stage);
      result.put("error_type", root.getClass().getName());
      String message = root.getMessage();
      result.put("error", message == null ? root.getClass().getSimpleName() : message.substring(0, Math.min(1500, message.length())));
    }
    result.put("phase_evidence", progress.evidence);
    // A new request must independently inspect committed records after this action.
    response.setValue("core_result", result);
  }
  public void inspect(ActionRequest request, ActionResponse response) {
    guard(); response.setValue("core_result", Beans.get(NativeGateService.class).inspect(caseId(request)));
  }
}
