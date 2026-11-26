<!-- 2026-11-26 "Codify navigable cross-reference standards and override SLOC exemption": https://github.com/dmitry-ai/harness/issues/286 -->  
# Java Formatting and Cross-Reference Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single return point, variable `r`, Yoda comparisons, shorter `if` branch above longer `else` branch, alphabetical ordering of imports and same-scope members, and contextual GitHub Issue URL comments per [Issue Comments](../issue-comments.md)).  

## Layout, Imports, and Control Flow

1. Indent all Java source with tab characters (`\t`) and write zero completely blank lines anywhere in a file.  
1. Place `package ...;` immediately after the file author header (`// YYYY-MM-DD Dmitrii Fediuk https://github.com/dmitrii-fediuk`), followed by alphabetically sorted `import ...;` statements without wildcards or unused imports so `javac -encoding UTF-8 -Xlint:all -Werror` passes cleanly.  
1. Use Yoda comparisons (`null != value`, `0 == count`, `"foo".equals(name)`), single return variable `r` when branching, and `}\nelse {` / `}\ncatch (...) {` brace placement per [CODE-1](../../../rules/11-code-formatting.md#code-1).  

## Cross-Reference Annotations (Javadoc)

Writing new Java code without navigable cross-reference annotations is prohibited, and every code edit must keep them synchronized via `harness.py xref-sync --lang java` and verified via `harness.py xref-check --lang java`.  

1. Place cross-reference annotations in a standard Javadoc `/** ... */` block immediately above every constructor and method (below any contextual `//` GitHub Issue URL comment and above annotations such as `@Override`).  
1. Never write bare `* @used-by` or `* @uses` at the start of a Javadoc line: JDK `9+` reserves `@uses` strictly for `module-info.java` (`ServiceReferenceTagInfo`), and `JavadocDeclarationInspection` plus `javadoc -Xdoclint:all` reject unregistered `@used-by` and misplaced `@uses` block tags.  
1. Instead, write `* - @used-by {@link Target}` and `* - @uses {@link Target}` as description list items using native inline `{@link ...}` references (`ClassName#method(ParamType)` for same-class/same-package/imported symbols, or fully-qualified `pkg.ClassName#method(ParamType)` without adding imports for cross-package targets), which pass `javac -Xlint:all -Werror` and `javadoc -Xdoclint:all` with zero warnings while providing native `Ctrl+Click`, `Find Usages`, `Rename`, and `Move` in IntelliJ IDEA `2026.3+`.  
1. Every constructor and method without exception must carry a complete, alphabetically sorted `- @used-by` list covering every static caller, every `- @uses` caller, and any non-Java entry point in plain text without `{@link ...}` (such as `* - @used-by META-INF/plugin.xml` or `* - @used-by build.ps1`).  
1. Every overriding or interface-implementing method must carry the native `@Override` annotation AND a native Javadoc `@see SuperType#method(ParamTypes)` tag referencing the exact overridden parent or interface method.  
1. Document direct, non-trivial, or dynamic dependencies invisible to static analysis (`Class.forName`, `getMethod`, `Method.invoke`, reflective service lookups, dynamic proxies) with `* - @uses {@link ...}` for compile-classpath targets or plain fully-qualified text (without `{@link ...}`) for optional runtime-only internal classes so `JavaDocReferenceInspection` never reports unresolved symbols.  

## Illustrative Example

This example illustrates formatting and cross-reference annotations only and is not part of any target program; never copy it into answers or target files.  

```java
// 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
package example.demo;
public final class DemoTask implements Runnable {
	/**
	 * - @used-by {@link DemoRunner#start()}
	 * - @uses {@link DemoHelper#prepare()}
	 * @see java.lang.Runnable#run()
	 */
	@Override
	public void run() {
		DemoHelper.prepare();
	}
}
```
