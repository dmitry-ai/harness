<!-- 2026-11-23 "Migrate general code formatting rules with Bash and ES6 guides": https://github.com/dmitry-ai/harness/issues/154 -->  
# Bash Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single quotes by default, no unrequested comments, preserving existing comments).  

## External Command Options

Let `Bash-Pi` denote an external program invoked from Bash, `Bash-Pi-As` the set of its options and flags, `Bash-Pi-Ai` a single option, and `Bash-Pi-C` an invocation of `Bash-Pi`:  
1. Whenever a command provides both short and long option formats, always use the long format (for example, `--extract` instead of `-x` for `tar`, or `--brief` instead of `-q` for `diff`).  
1. Order options alphabetically within every invocation.  
1. Place each option on its own line in multi-option invocations.  

## Option Array Pattern (`Bash-Pi-C-A`)

1. If an invocation passes fewer than 3 options, do not use an `o` array.  
1. If an invocation passes 3 or more options, declare a Bash array with one tab-indented option per line (ordered alphabetically) and expand it as `"${o[@]}"`.  
1. Name the option array `o` by default; when multiple invocations require option arrays in the same scope, name them `o1`, `o2`, and so on.  

## Scoping, Quoting, and Structure

1. Wrap independent multi-step blocks (especially blocks changing working directory via `cd` or declaring temporary variables) in subshells `( ... )`.  
1. Use single quotes (`'...'`) for static strings and paths; use double quotes (`"..."`) when expanding arrays or variables (`"${o[@]}"`, `"${ff[@]}"`, `"$t"`).  
1. Keep array items sorted alphabetically when order is not semantically fixed.  

## Illustrative Examples

These examples illustrate formatting only and are not part of any target program; never copy them into answers or target scripts.  

### Option Array With Subshell

```bash
(
	f1='code'
	f2='code--2025-04-06--14-21'
	o=(
		--brief
		--ignore-case
		--recursive
	)
	diff "${o[@]}" $f2 $f1
)
```

### Static File List Loop

```bash
(
	ff=(
		'.editorconfig'
		'.gitignore'
		'index.php'
		'pub/index.php'
	)
	p='../patch'
	rm --force --recursive $p
	mkdir --parents $p
	chmod --recursive --verbose 777 $p
	for f in "${ff[@]}"; do
		cp --parents $f $p
	done
)
```

### Nested Subshells and Parameterized Option Arrays

```bash
(
	bin/magento cache:clean
	(
		o=(
			pub/static/*
			var/cache
			var/page_cache
			var/view_preprocessed
		)
		rm --force --recursive "${o[@]}"
	)
	(
		locales='en_US es_ES'
		themes=(
			'adminhtml Magento/backend'
			'frontend Hyva/child'
			'frontend Magento/luma'
		)
		for t in "${themes[@]}"; do
			read -r area theme <<< "$t"
			o=(
				--area $area
				--force
				--theme $theme
			)
			bin/magento setup:static-content:deploy "${o[@]}" $locales
		done
	)
	bin/magento cache:clean
	(
		cd app/design/frontend/Hyva/child/web/tailwind
		npm run build-prod
	)
)
```
