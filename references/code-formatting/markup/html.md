# HTML Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single quotes by default, no unrequested comments).  
Derived from `mage2pro/core` HTML templates (`10` `.html` files).  

## Indentation, Attributes, and Expressions

1. Use UTF-8 encoding, LF line endings, tab indentation (`\t`), and zero blank lines.  
1. Enclose HTML attribute values in single quotes (`'...'`) by default (`<div class='field date required'>`, `<label class='label'>`).  
1. Use double quotes (`"..."`) on an attribute only when its value contains single-quoted expressions (such as Knockout `data-bind="attr: {id: fid('cc_type_exp_div')}"`).  
1. Inside multi-line structured attribute values (for example, multi-line `data-bind` objects), indent continuation lines with tabs, order keys alphabetically where semantics allow, and place a leading comma `,` at the start of each continuation entry.  
1. Preserve existing template comments (`<!-- ko ... -->` bindings and existing notes) untouched per [FILE-1](../../../rules/01-file-boundaries.md#file-1).  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```html
<div class='field date required' data-bind="attr: {id: fid('cc_type_exp_div')}">
	<label class='label' data-bind="attr: {for: fid('expiration')}">
		<span><!-- ko df_i18n: 'Expiration Date'--><!-- /ko --></span>
	</label>
	<div class='control'>
		<select class='select month' data-bind="
			attr: {
				'data-container': getCode() + '-cc-month'
				,id: fid('expiration')
			}
			,enable: true
			,value: creditCardExpMo
		"></select>
	</div>
</div>
```
<!-- https://github.com/dmitry-ai/harness/issues/155 -->  
