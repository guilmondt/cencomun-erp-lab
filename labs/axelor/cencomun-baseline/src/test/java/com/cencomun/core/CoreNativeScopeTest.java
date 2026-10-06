package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import jakarta.ws.rs.ForbiddenException;
import org.junit.jupiter.api.Test;

class CoreNativeScopeTest {
  @Test void directCallsAreDeniedAndScopeDoesNotLeakAfterFailure() {
    assertThrows(ForbiddenException.class,CoreNativeScope::require);
    assertThrows(IllegalStateException.class,()->{try(CoreNativeScope scope=CoreNativeScope.enter()){CoreNativeScope.require();throw new IllegalStateException("native failure");}});
    assertThrows(ForbiddenException.class,CoreNativeScope::require);
  }
  @Test void nestedCallsDoNotOpenAnotherThread() throws Exception {
    try(CoreNativeScope outer=CoreNativeScope.enter()) {
      try(CoreNativeScope inner=CoreNativeScope.enter()){CoreNativeScope.require();}
      CoreNativeScope.require();
      java.util.concurrent.atomic.AtomicBoolean denied=new java.util.concurrent.atomic.AtomicBoolean();
      Thread thread=new Thread(()->{try{CoreNativeScope.require();}catch(ForbiddenException e){denied.set(true);}});thread.start();thread.join();assertTrue(denied.get());
    }
    assertThrows(ForbiddenException.class,CoreNativeScope::require);
  }
}
