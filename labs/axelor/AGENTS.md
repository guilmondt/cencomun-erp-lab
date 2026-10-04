# Axelor-specific instructions

Scope: labs/axelor/**

- Keep Cencomun code in an isolated custom Axelor module/package under com.cencomun.*.
- Do not edit Axelor Open Suite/Open Platform modules to implement Cencomun features.
- Prefer model/view/action/service/repository extension mechanisms documented by Axelor.
- Use Java 21 and the project Gradle wrapper.
- Pin AOS/AOP according to versions.lock.
- Business logic belongs in services/model logic, not ad-hoc database writes.
- Money/business calculations require server-side tests.
