package com.cencomun.core;

import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;

/** Three explicit fixture HTTP boundaries; posting remains one native transaction. */
public class NativeBankBookController {
  public void prepare(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    NativeGateService fixture = Beans.get(NativeGateService.class);
    NativeGateService.Progress progress = new NativeGateService.Progress();
    fixture.activate(progress);
    fixture.prepare(progress, "BANKBOOK");
    response.setValue("core_result", Beans.get(NativeBankBookService.class).configure());
  }
  public void post(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result", Beans.get(NativeBankBookService.class).post());
  }
  public void inspect(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result", Beans.get(NativeBankBookService.class).inspect());
  }
}
