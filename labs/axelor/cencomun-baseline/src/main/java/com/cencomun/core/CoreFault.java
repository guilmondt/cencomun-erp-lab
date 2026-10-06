package com.cencomun.core;

/** Shared contract status; HTTP mapping occurs only after the service transaction ends. */
public final class CoreFault extends RuntimeException {
  public final int status;
  public CoreFault(int status, String message) { super(message); this.status = status; }
}
