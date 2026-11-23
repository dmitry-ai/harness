# XML Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single quotes by default, alphabetical ordering, no unrequested comments).  
Derived from `mage2pro/core` (`126` `.xml` files).  

## Declaration, Encoding, and Quotes

1. Start every XML document with a single-quoted declaration `<?xml version='1.0'?>` (omit `encoding='UTF-8'` unless explicitly required, keeping single quotes if present).  
1. Use UTF-8 encoding, LF line endings, tab indentation (`\t`), and zero blank lines.  
1. Always enclose XML attribute values in single quotes (`'...'`).  

## Attributes, Wrapping, and Tags

1. Order attributes alphabetically (case-insensitive) on every element (`defer='defer' src='...'`, `frontName='...' id='...'`, `instance='...' name='...'`).  
1. When attributes wrap across multiple lines, indent each attribute (or tightly coupled attribute group such as `showInDefault='1' showInWebsite='1' showInStore='1'`) by one tab on its own line, and place the closing `>` or `/>` on its own line aligned with the opening `<tag`.  
1. Omit the space before `/>` in self-closing tags (`<module name='Df_Core'/>`, `<block class='Df\Checkout\B\Messages'/>`).  
1. Keep short single-child wrappers compact on one line (`<head><css src='Df_Checkout::index.css'/></head>`, `<arguments><argument name='domDocumentClass' xsi:type='string'>Df\Framework\Config\Dom</argument></arguments>`).  
1. When block comments (`<!-- ... -->`) are required or preserved, align them at column 0 without leading tab indentation.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```xml
<?xml version='1.0'?>
<config
	xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
	xsi:noNamespaceSchemaLocation='urn:magento:framework:Event/etc/events.xsd'
>
	<event name='core_copy_fieldset_order_address_to_customer'>
		<observer
			instance='Df\Customer\Observer\CopyFieldset\OrderAddressToCustomer'
			name='Df\Customer\Observer\CopyFieldset\OrderAddressToCustomer'
		/>
	</event>
	<event name='customer_register_success'>
		<observer instance='Df\Customer\Observer\RegisterSuccess' name='Df\Customer\Observer\RegisterSuccess'/>
	</event>
</config>
```
<!-- https://github.com/dmitry-ai/harness/issues/155 -->  
