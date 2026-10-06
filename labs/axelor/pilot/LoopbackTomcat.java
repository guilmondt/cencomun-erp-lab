package com.cencomun.pilot;
import org.apache.catalina.startup.Tomcat;
/** Local disposable UI harness using the pinned Tomcat public API. */
public final class LoopbackTomcat {
  public static void main(String[] args) throws Exception {
    if(args.length!=2)throw new IllegalArgumentException("WAR path and private runtime directory required");
    java.nio.file.Files.createDirectories(java.nio.file.Path.of(args[1],"webapps"));
    Tomcat tomcat=new Tomcat();tomcat.setBaseDir(args[1]);tomcat.setPort(18080);
    tomcat.getConnector().setProperty("address","127.0.0.1");
    var context=tomcat.addWebapp("/axelor-erp",new java.io.File(args[0]).getCanonicalPath());
    ((org.apache.tomcat.util.scan.StandardJarScanner)context.getJarScanner()).setScanClassPath(false);
    Runtime.getRuntime().addShutdownHook(new Thread(()->{try{tomcat.stop();}catch(Exception e){throw new RuntimeException(e);}}));
    tomcat.start();tomcat.getServer().await();
  }
}
