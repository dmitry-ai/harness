---
name: df-architecture
description: "Enforces grounding software architecture decisions, design proposals, structural GitHub issues, and structural code changes in canonical Software design patterns with independent read-only arch-auditor verification; applies automatically under ARCH-1/ARCH-2 and via /df-architecture."
---
<!-- 2026-11-26 "Add software design patterns normative contract and catalog": https://github.com/dmitry-ai/harness/issues/344 -->  
# Software Design Patterns and Architecture Auditing

This skill codifies the full Harness architecture protocol backing [ARCH-1](../../rules/12-architecture.md#arch-1) and [ARCH-2](../../rules/12-architecture.md#arch-2).  
Every software architecture decision made or proposed by an agent must be grounded in and explicitly described through established Software design patterns and architectural patterns/styles cataloged in [patterns-catalog.json](../../references/architecture/patterns-catalog.json).  

## 1. Normative Pattern Taxonomy

Canonical categories follow the Wikipedia Software design pattern reference (`https://en.wikipedia.org/wiki/Software_design_pattern`):  

1. **Creational** (`#Creational`): object and dependency creation mechanisms (for example Abstract Factory, Builder, Dependency Injection, Factory Method, Lazy Initialization, Object Pool, Prototype, Singleton).  
1. **Structural** (`#Structural`): module, class, and interface composition (for example Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Module, Proxy).  
1. **Behavioral** (`#Behavioral`): responsibility delegation and interaction protocols (for example Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Null Object, Observer, Specification, State, Strategy, Template Method, Visitor).  
1. **Concurrency** (`#Concurrency`): parallel and asynchronous coordination (for example Active Object, Double-Checked Locking, Guarded Suspension, Lock, Messaging, Monitor Object, Proactor, Reactor, Read-Write Lock, Scheduler, Thread Pool).  
1. **Architectural** (`#Related`): system-level software architecture patterns and styles (for example Layered Architecture, Hexagonal Architecture, Microkernel / Plugin Architecture, Event-Driven Architecture, Pipes and Filters, Model-View-Controller, Repository, Unit of Work, Intercepting Filter, Registry, Publish-Subscribe).  

Distinguish canonical design and architecture patterns from language-level implementation idioms.  

## 2. Mandatory Pattern Specification Format

In every structural parent GitHub issue (`## Architecture (Software Design Patterns)`), design plan, or architectural `/df-analysis` solution method (`M-*`), include all six GoF documentation fields (`#Documentation`) for each applied pattern:  

- **Pattern:** exact canonical pattern name (or registered alias) from [patterns-catalog.json](../../references/architecture/patterns-catalog.json).  
- **Category:** matching taxonomy category (`Creational`, `Structural`, `Behavioral`, `Concurrency`, or `Architectural`).  
- **Intent:** the concrete design problem or force the pattern resolves in this system.  
- **Participants:** exact module paths, classes, protocols, or functions implementing each pattern role.  
- **Collaboration:** how the declared participants interact and exchange state or control.  
- **Consequences:** concrete architectural benefits, trade-offs, and constraints accepted.  

Localized Russian field labels (`Паттерн`, `Категория`, `Назначение` / `Суть`, `Участники`, `Взаимодействие`, `Последствия`) are accepted equivalently.  

## 3. Controlled `idiom_exception` Against Cargo-Cult Overengineering

Per Wikipedia `#Criticism` (including Peter Norvig's observation that 16 of 23 GoF patterns simplify or dissolve into first-class language constructs), never wrap trivial language primitives in artificial GoF boilerplate.  
When a native language feature (such as Python first-class callables, closures, decorators, `Protocol`, context managers, or generators) replaces classic GoF scaffolding, declare an explicit `idiom_exception` block containing four required fields:  

- **Pattern:** the canonical GoF pattern displaced by the native language construct.  
- **Native Construct:** the exact language feature replacing the pattern scaffolding.  
- **Rationale:** why adding classic GoF wrapper classes would introduce unjustified complexity (`>= 20` characters).  
- **Participants:** the exact concrete modules or functions using the native construct.  

Every `idiom_exception` remains subject to adversarial verification by `arch-auditor` to prevent disguised bypasses.  

## 4. Objective Structural Trigger Criteria

Deterministic Protection Proxy checks activate on concrete structural signals rather than isolated keywords:  

1. **Code triggers:** creating a new production module (`>= 10` executable SLOC or defining a class/public API), adding a new class / `Protocol` / `ABC`, introducing new cross-module imports, modifying Harness registries or hooks (`gates/`, `cli_registry.py`, `staged_gates.py`, `runtime.json` roles), or changing `>= 2` production files / `>= 30` executable SLOC.  
1. **Issue and response triggers:** parent GitHub issues proposing structural features or refactors, architectural `/df-analysis` solution methods (`M-*`) defining modules/classes/hooks/gates/APIs/layers/subsystems, or explicit `task_flags: ["architecture_change"]`.  

Trivial single-file bugfixes (`< 30` SLOC, no new classes, no new cross-module imports, no registry edits), test-only edits, and comment-only edits do not trigger mandatory `arch-auditor` review.  

## 5. Independent `arch-auditor` Falsifier Protocol

All architectural audits run through the dedicated read-only native subagent `arch-auditor` (`ARCH` role in `runtime.json`: `invoke_subagent` in Antigravity, `spawn_agent` in Codex) without hidden CLI LLM sessions (`REVIEW-1`).  
Immutable packages and verdict receipts live exclusively inside `<project>/ꘖ/data/arch-reviews/` (`FILE-5`, `FILE-6`).  

1. **Freeze package:** run `python <scripts>/harness.py arch-prepare <project> --parent <conversation-uuid> --kind design|code_diff|response [--response-file <path>] [--spec-file <path>] [--repo <path>] [--issue <url>]` to freeze the candidate specification, code diff, or response under `package_sha256` and `module_hashes`.  
1. **Invoke neutral read-only auditor:** pass only the exact project root and frozen package path to `arch-auditor` without pre-filling `"approved"` or biasing the verdict.  
1. **Verify package inside auditor:** `arch-auditor` runs `python <scripts>/harness.py arch-review-input <project> --package <rel-path>`, reads the full frozen spec/diff/response without truncation, and falsifies four violation classes:  
   - `missing_pattern`: architecture lacks canonical Software design / architectural pattern grounding.  
   - `pattern_washing`: declared `Participants` or `Collaboration` disagree with real classes, functions, or dependencies in code or design.  
   - `disguised_refactor`: structural change disguised as a minor fix or backed by an unjustified `idiom_exception`.  
   - `cargo_cult`: unnecessary GoF complexity where a simpler pattern or native language idiom is objectively better.  
1. **Single final verdict:** `arch-auditor` returns one JSON verdict (`schema_version: 1`, `review_mode: "falsifier"`, `package`, `package_sha256`, `result`, `summary`, `pattern_checks`, `findings`) directly in its final native response without duplicating it via `send_message`.  
1. **Record verified verdict:** the primary agent runs `python <scripts>/harness.py arch-record-review <project> --report <path> --parent <parent-uuid> --reviewer <reviewer-uuid> [--wait-timeout <S>] --consume-input`, verifying native provenance (`role='ARCH'`), read-only isolation, and schema integrity.  
1. **Inspect status:** run `python <scripts>/harness.py arch-check <project> [--repo <path>] [--response-file <path>] [--issue <url>]` at any time for read-only diagnostics.  

Any `needs_changes` verdict or open `significant`/`critical` finding keeps `ARCH-AUDIT-GATE` (`PreToolUse` priority `105`), `ANSWER_GATES`, `STOP_GATES`, and Git `pre-commit` closed until the architecture or code is revised and approved on a new `package_sha256`.  
Unchanged production modules whose content SHA-256 already carries an `approved` receipt are served from the `module_hashes` cache to avoid redundant auditor turns.  
