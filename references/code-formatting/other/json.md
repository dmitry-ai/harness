# JSON Formatting Standard

Inherits [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, alphabetical key ordering where semantics allow) subject to strict RFC 8259 JSON syntax: all keys and strings MUST use double quotes (`"..."`) and comments are forbidden.  
Derived from `mage2pro/core` (`composer.json`, `Core/etc/df.json`) and Python JSON serialization conventions.  

## Hand-Authored JSON Manifests

1. Use UTF-8 encoding without BOM, LF line endings, tab indentation (`\t`), and zero blank lines.  
1. Place a leading comma `,` at the start of each continuation line in multi-line objects and arrays.  
1. Keep short nested objects and arrays compact on a single line (`"autoload": {"files": ["registration.php"], "psr-4": {"Df\\": ""}}`, `"authors": [{ ... }]`).  
1. Order object keys alphabetically inside maps whose key order is not semantically fixed (such as `require` dependencies).  

## Programmatically Serialized JSON Output

1. Format generated JSON output with tab indentation (`indent='\t'` in Python, `'\t'` in JavaScript `JSON.stringify`).  
1. Preserve non-ASCII UTF-8 characters unescaped (`ensure_ascii=False` in Python).  
1. Sort keys alphabetically (`sort_keys=True`) when deterministic diffs and stable reports are required.  
1. Standard trailing-comma-free output produced by native JSON serializers is expected for generated files; do not post-process serializer output into leading commas.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```json
{
	"name": "mage2pro/core"
	,"version": "11.5.8"
	,"require": {
		"ext-curl": "*"
		,"magento/framework": ">=100.0.0"
		,"phpunit/phpunit": "*"
	}
	,"autoload": {"files": ["registration.php"], "psr-4": {"Df\\": ""}}
}
```
<!-- https://github.com/dmitry-ai/harness/issues/155 -->  
