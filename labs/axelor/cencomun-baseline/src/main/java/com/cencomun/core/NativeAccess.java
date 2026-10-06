package com.cencomun.core;

import com.axelor.db.JpaRepository;
import com.axelor.db.Model;
import com.axelor.db.Query;
import com.axelor.inject.Beans;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;

/** Pinned runtime API bridge: model repositories for catalog, native services for effects.
 * No SQL, no status manipulation, and no swallowed API incompatibilities.
 * This keeps the independent AOP baseline build separate from the full AOS runtime.
 */
public final class NativeAccess {
  @SuppressWarnings("unchecked")
  public static Class<Model> type(String name) {
    if (!name.startsWith("com.axelor.")) throw new IllegalArgumentException("Not an Axelor API");
    try { return (Class<Model>) Class.forName(name); }
    catch (ClassNotFoundException e) { throw new IllegalStateException("Pinned native API unavailable: " + name, e); }
  }
  public static Object service(String name) { return Beans.get(type(name)); }
  public static Model create(String name) {
    try { return type(name).getConstructor().newInstance(); }
    catch (ReflectiveOperationException e) { throw new IllegalStateException(e); }
  }
  @SuppressWarnings("unchecked")
  public static Model save(Model model) {
    return JpaRepository.of((Class<Model>) (Class<?>) model.getClass()).save(model);
  }
  public static Model one(String name, String filter, Object... values) {
    return Query.of(type(name)).filter(filter, values).fetchOne();
  }
  public static List<Model> list(String name, String filter, Object... values) {
    return Query.of(type(name)).filter(filter, values).fetch();
  }
  public static Object get(Object obj, String property) { return call(obj, "get" + cap(property)); }
  public static void set(Object obj, String property, Object value) { call(obj, "set" + cap(property), value); }
  private static String cap(String s) { return Character.toUpperCase(s.charAt(0)) + s.substring(1); }
  private static Class<?> box(Class<?> t) {
    if (t == int.class) return Integer.class; if (t == boolean.class) return Boolean.class;
    if (t == long.class) return Long.class; return t;
  }
  public static Object call(Object obj, String method, Object... args) {
    List<Method> candidates = Arrays.stream(obj.getClass().getMethods()).filter(m -> {
      if (!m.getName().equals(method) || m.getParameterCount() != args.length || m.isBridge()) return false;
      for (int i = 0; i < args.length; i++)
        if (args[i] != null && !box(m.getParameterTypes()[i]).isInstance(args[i])) return false;
      return true;
    }).toList();
    if (candidates.size() != 1) throw new IllegalStateException("Pinned API signature mismatch: "
        + obj.getClass().getName() + "." + method + "/" + args.length + ", matches=" + candidates.size());
    try { return candidates.getFirst().invoke(obj, args); }
    catch (InvocationTargetException e) {
      Throwable cause = e.getCause();
      if (cause instanceof RuntimeException r) throw r;
      throw new NativeFailure(cause);
    } catch (ReflectiveOperationException e) { throw new IllegalStateException(e); }
  }
  public static final class NativeFailure extends RuntimeException {
    public NativeFailure(Throwable cause) { super(cause); }
  }
  private NativeAccess() {}
}
