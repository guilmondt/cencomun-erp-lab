package com.cencomun.core;

import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;

public class NativeFxController {
  public void prepare(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result", Beans.get(NativeFxService.class).prepare());
  }
  public void inspect(ActionRequest request, ActionResponse response) {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result", Beans.get(NativeFxService.class).inspect());
  }
}
