# Product Requirement Document (PRD)

## Project: Superterminal (v1.0)

**Document Status:** Draft

**Target Release:** Q3 2026

**Author:** Qasim & AI Collaborator

---

## 1. Executive Summary & Objective

Superterminal is a lightweight, high-performance global CLI tool designed to lower the barrier to entry for terminal operations. It replaces complex, syntax-heavy terminal commands with natural English language.

Unlike separate GUI applications or isolated AI chat boxes, Superterminal runs entirely inside the user’s native shell environment via an interactive sub-shell wrapper. The goal is to provide a fluid, seamless workflow where experienced developers can bypass mnemonic fatigue and beginners can use advanced utilities safely, keeping the user in full control of final command execution.

---

## 2. User Personas & Problem Alignment

| Persona | Core Pain Point | Superterminal Value Proposition |
| --- | --- | --- |
| **The Junior Developer / Student** | Intimidated by complex CLI syntax, flags, and cross-platform differences (e.g., CMD vs. Bash). | Can express intent naturally without breaking flow to search documentation. |
| **The Polyglot / DevOps Engineer** | Context-switching between platforms leads to syntax errors (e.g., forgetting Windows equivalents for `tar`, `find`, or network tools). | Provides a single unified natural language interface across Windows, macOS, and Linux. |

---

## 3. Product Architecture & Technical Bounds

### 3.1 Global System Architecture

Superterminal will be compiled and distributed as a self-contained **Global CLI Binary** (e.g., built in Go or Rust) to ensure sub-millisecond initialization and cross-platform compatibility.

### 3.2 Environment Constraints

* **Active Detection:** The binary must dynamically detect the host Operating System and parent shell process upon initialization.
* **Zero File-System Context Tracking:** For speed, privacy, and simplicity, Superterminal does *not* read or index the user's local directory trees, files, or histories. The natural language input must explicitly state identifiers (e.g., `"delete folder project-alpha"` instead of `"delete this folder"`).

---

## 4. Detailed Feature & Functional Requirements

### 4.1 Feature: Interactive Session Management (`Super` Environment)

* **Requirement ID:** FR-001
* **Description:** The user initializes the natural language shell state by running a specific command keyword.
* **Functional Specification:**
* Typing `Super` followed by `Enter` invokes the binary and suspends normal shell evaluation.
* The terminal prompt must change to visually display state mutation, replacing the standard platform prompt with `Super > `.
* Typing 'exit', 'quit' or 'leave' all three should do that (case-insensitive), and pressing `Enter` must cleanly close the sub-shell thread and return the user safely to their native parent shell context.



### 4.2 Feature: Cross-Platform Environment Mapping

* **Requirement ID:** FR-002
* **Description:** Natural language must translate accurately into the correct syntax of the *detected* runtime shell environment.
* **Functional Specification:**
* The translation layer must output shell-specific scripts.
* *Example Intent:* `"show all files including hidden ones"`
* **Windows Command Prompt (cmd):** Output `dir /a`
* **macOS / Linux (Zsh / Bash):** Output `ls -a`





### 4.3 Feature: Command Intent Classification (Read-Only vs. Modifying)

* **Requirement ID:** FR-003
* **Description:** To maximize workflow efficiency while preserving absolute security, Superterminal must bifurcate incoming commands into two structural execution pipelines based on intent.

```
                  [ User inputs Natural Language ]
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
            [ Read-Only Intent ]    [ Modifying Intent ]
                     │                       │
         (Execute Instantly & Print)   (Inject Inline to Prompt)
                     │                       │
                     ▼                       ▼
             [ Return to Super > ]   [ User Edits/Confirms -> Enter ]

```

#### Pipeline A: The Read-Only Fast Track

* **Criteria:** Queries that simply retrieve, view, or parse data without changing state (e.g., reading logs, listing structures, checking status, viewing paths).
* **Execution Behavior:** Superterminal translates the natural language query, passes it directly to the system kernel for execution, prints the output logs cleanly, and drops the cursor down to a fresh `Super > ` line immediately. Only **one** user `Enter` stroke is needed.

#### Pipeline B: The Modifying Track (Human Guardrail)

* **Criteria:** Queries that write, delete, overwrite, provision, deploy, clone, or manipulate file systems, settings, or remote environments (e.g., `mkdir`, `rm`, `git clone`, `chmod`).
* **Execution Behavior:** Superterminal translates the prompt but **strictly forbids automatic execution**. Instead, it intercepts the input pipeline and dynamically injects the raw shell text string directly onto the next interactive line.

### 4.4 Feature: Inline Text Injection & Manipulation

* **Requirement ID:** FR-004
* **Description:** The user must be allowed full terminal capabilities over the generated modifying string.
* **Functional Specification:**
* When a Modifying Command string is injected onto the line, the cursor must sit at the end of the text.
* The user must have full terminal navigation: arrow keys to traverse, backspace to eliminate text, and keys to insert custom arguments or configurations manually.
* **The Ultimate Guardrail:** Execution *only* triggers when the user actively strikes the `Enter` key a second time on that modified or approved command.



---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Performance & Latency

* The translation engine latency (from hitting `Enter` on natural language to displaying the generated command or output) must not exceed **250ms**.
* Binary load time when typing `Super` must be imperceptible (< 50ms).

### 5.2 Security & Privacy

* Because translation happens inside the user terminal environment, zero operational shell logs or sensitive credentials handled in natural language statements should be retained externally by Superterminal.

---

## 6. Key Verification Scenarios (UAT)

### Scenario 1: The Fast-Track View

1. User types `Super` $\rightarrow$ System enters sub-shell (`Super > `).
2. User types `check my git branch status` and hits `Enter`.
3. System classifies as **Read-Only**, executes `git status`, outputs branch info, and serves a new `Super > ` line.

### Scenario 2: The Inline Edit Guardrail

1. User types `create folder called test-environment` inside `Super > ` and hits `Enter`.
2. System classifies as **Modifying**, prints `mkdir test-environment` on the next line, and leaves the cursor blinking.
3. User uses left-arrow keys, changes `test-environment` to `prod-environment`, and hits `Enter`.
4. System executes `mkdir prod-environment` and displays a new `Super > ` line.

### Scenario 3: Exiting

1. User types `Exit Super` inside `Super > ` and hits `Enter`.
2. System tears down the sub-shell wrapper and drops user safely into `C:\Users\Arfa>` or `~/`.