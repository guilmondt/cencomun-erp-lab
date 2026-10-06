package com.cencomun.core;

/** Custom repositories accept writes only through module services, never generic REST. */
public final class CoreWriteScope implements AutoCloseable {
  private static final ThreadLocal<Integer> DEPTH = ThreadLocal.withInitial(() -> 0);
  private CoreWriteScope() { DEPTH.set(DEPTH.get()+1); }
  static CoreWriteScope enter() { return new CoreWriteScope(); }
  public static void require() { if(DEPTH.get() == 0) throw new CoreFault(403,"Use the authenticated Cencomun workflow service"); }
  public void close() { int depth=DEPTH.get()-1; if(depth==0) DEPTH.remove(); else DEPTH.set(depth); }
}
