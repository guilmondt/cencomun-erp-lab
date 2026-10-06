package com.cencomun.core;

import jakarta.ws.rs.ForbiddenException;

/** Private scope opened only by module calls after their actor/company checks. */
final class CoreNativeScope implements AutoCloseable {
  private static final ThreadLocal<Integer> DEPTH=ThreadLocal.withInitial(()->0);
  private CoreNativeScope(){DEPTH.set(DEPTH.get()+1);}
  static CoreNativeScope enter(){return new CoreNativeScope();}
  static void require(){if(DEPTH.get()==0)throw new ForbiddenException("Permission denied: authenticated Core workflow required for native writes");}
  @Override public void close(){int depth=DEPTH.get()-1;if(depth==0)DEPTH.remove();else DEPTH.set(depth);}
}
