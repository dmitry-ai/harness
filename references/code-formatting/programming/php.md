<!-- 2026-11-23 "Add PHP and markup formatting standards derived from mage2pro/core": https://github.com/dmitry-ai/harness/issues/155 -->  
# PHP Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single return point, variable `$r`, Yoda comparisons, shorter `if` branch above longer `else` branch, single quotes by default, alphabetical ordering, no unrequested comments).  
Derived from `mage2pro/core` (`765` `.php` files).  

## File Framing, Namespaces, and Imports

1. Start line 1 with `<?php`, omit the closing `?>` tag in pure PHP files, and omit `declare(strict_types=1);` unless the target codebase explicitly requires it.  
1. Use UTF-8 encoding, LF line endings, and tab indentation (`\t`).  
1. Place `namespace ...;` directly below `<?php` and `use ...;` imports directly below `namespace` without blank lines.  
1. Keep `use` imports sorted alphabetically (case-insensitive).  
1. Use short uppercase aliases for frequently referenced classes (for example, `use Throwable as Th;`, `use Magento\Sales\Model\Order as O;`), and alias an extended parent class as `_P` (`use Magento\Framework\View\Element\AbstractBlock as _P;`).  

## Classes, Visibility, and Members

1. Declare concrete classes as `final class` by default unless designed for inheritance (`abstract class` or extensible `class`).  
1. Place the opening `{` on the same line as the `class`, `interface`, or `trait` header.  
1. Omit the redundant `public` keyword on public methods and class constants (`function file():string`, `const KEY = 'value';`); always write `protected` and `private` explicitly.  
1. Prefer `private` properties over `protected` or `public`, prefixing non-public property names with a leading underscore (`private $_a;`).  
1. Order class methods by visibility (public/implicit, then `protected`, then `private`) and alphabetically within each visibility group; order standalone functions in a file alphabetically.  

## Functions, Return Types, Closures, and Casts

1. Place the opening `{` on the same line as every function or method signature.  
1. Write return type declarations with no space after the colon (`function file():string`, `function line():int`, `function isPHTML():bool`, `function run():void`).  
1. Keep single-statement functions and methods on a single compact line (`function line():int {return (int)$this['line'];}`).  
1. Write closures with no space after `function` and no space after `use` (`function(string $k, array $v):array use($ctx) { ... }`).  
1. Write type casts with no space between the cast and the operand (`(int)$this['line']`, `(string)$v`).  

## Arrays, Strings, Operators, and Comments

1. Always use short array syntax `[...]` instead of `array(...)`.  
1. Surround `=>` and string concatenation `.` with single spaces (`'key' => $value`, `$a . $b`).  
1. In multi-line arrays and argument lists, use a leading comma `,` at the start of each continuation line instead of trailing commas.  
1. Use single quotes (`'...'`) by default; use double quotes (`"..."`) only for variable interpolation (`"{$libDir}/{$c}"`, `"$s1 ($s2)"`) or escape sequences (`"\n"`).  
1. Use strict comparisons (`===`, `!==`) with constants on the left (`null === $r`, `false === $pos`, `0 === count($a)`), concise ternary (`? :`) and Elvis (`?:`) expressions, single return point with `$r`, and `}\nelse {` with the shorter branch first.  
1. Keep single-statement `try`, `catch`, and `finally` blocks compact on single lines when clear (`try {$r = run();}\ncatch (Th $th) {$r = $fallback;}`).  
1. When a single-line comment is explicitly required (such as an [EXEC-5](../../../rules/08-execution-and-tools.md#exec-5) GitHub Issue URL) or already present, use `#` rather than `//`.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```php
<?php
namespace Df\Example;
use Df\Core\O as _P;
use Throwable as Th;
final class Frame extends _P {
	function file():string {return !($r = (string)$this['file']) ? $r : df_path_rel($r);}
	function format(string $prefix, array $extra = []):string {
		$items = [
			'file' => $this->file()
			,'line' => $this->line()
		] + $extra;
		try {$r = $this->render($prefix, $items);}
		catch (Th $th) {$r = '';}
		return $r;
	}
	function line():int {return (int)$this['line'];}
	private function render(string $prefix, array $items):string {
		if (!$items) {
			$r = $prefix;
		}
		else {
			$parts = array_map(
				function(string $k, $v) use($prefix):string {return "{$prefix}:{$k}=" . (string)$v;}
				,array_keys($items)
				,$items
			);
			$r = implode(' ', $parts);
		}
		return $r;
	}
}
```
