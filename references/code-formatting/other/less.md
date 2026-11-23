# LESS Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single quotes by default, no unrequested comments).  
Derived from `mage2pro/core` LESS stylesheets (`25` `.less` files).  

## Selectors, Braces, and Rules

1. Use UTF-8 encoding, LF line endings, tab indentation (`\t`), and zero blank lines.  
1. Place opening `{` on the same line as the selector.  
1. Keep short single-declaration or compact two-declaration rules on a single-line block (`.df-integer {padding-left: 0.25em;}`, `.df-decimals {font-size: 80%; vertical-align: super;}`).  
1. Use a leading comma `,` on continuation lines when splitting long selector lists across multiple lines (`,#payment-methods > .item-title {`).  
1. Keep tightly scoped nested wrapper selectors compact when chained cleanly (`body {&.checkout-index-index, &.multishipping-checkout-billing { ... }}`).  
1. When a comment is explicitly required (such as an [EXEC-5](../../../rules/08-execution-and-tools.md#exec-5) GitHub Issue URL) or already present, use `//` single-line comments in LESS.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```less
.df-money {
	font-weight: 600;
	.df-integer {padding-left: 0.25em;}
	.df-decimals {font-size: 80%; vertical-align: super;}
}
body {&.checkout-index-index, &.multishipping-checkout-billing {
	.choice
	,#payment-methods > .item-title {
		> input[type=radio], > label {vertical-align: middle; margin-top: 0;}
		> input[name=billing-address-same-as-shipping] {vertical-align: sub;}
	}
}}
```
<!-- https://github.com/dmitry-ai/harness/issues/155 -->  
