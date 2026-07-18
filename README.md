# SuperTerminal 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

**SuperTerminal** is an AI-powered terminal assistant designed to bridge the gap between natural language and the command line. It translates complex tasks into executable shell commands, explains system outputs, troubleshoots errors in real-time, and automates multi-step terminal workflows—all without leaving your shell.

---
![SuperTerminal demo](https://drive.google.com/uc?export=view&id=1LVQ06ubWWNYPIZ2syKKGWkhlQ73JRhHh)


## 📖 Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Future Roadmap](#-future-roadmap)
- [Contribution Guidelines](#-contribution-guidelines)
- [License](#-license)

---

## ✨ Features

- **Natural Language to Shell**: Convert plain English prompts (e.g., `"find all log files modified in the last 24h and compress them"`) directly into syntax-valid CLI commands.
- **Forgiving Input**: You do not need perfect terminal syntax, exact wording, or flawless spelling. Ask naturally, and SuperTerminal will infer the command you meant.
- **Context-Aware Recommendations**: Understands your current OS, shell (bash, zsh, powershell), directory context, and command history to provide tailored assistance.
- **Real-Time Error Troubleshooting**: Automatically captures stderr from failed commands and explains the root cause along with a one-click fix.
- **Interactive Multi-Step Workflows**: Guides you through complex operations (e.g., setting up Docker environments, configuring CI/CD pipelines) using interactive prompt menus.
- **Safety First & Verification**: Dry-run preview mode lets you inspect, edit, or reject generated commands before execution.
- **Gemini Integration**: Uses Google Gemini for natural-language command translation, with the API key stored locally on first run.
- **Voice Input (Siri-style)**: Launch with `supervoice` and a floating mic button appears. Hold it, speak a command ("show me all python files"), release — Gemini turns the speech directly into a shell command, with the same read-only/modifying safety gate as typed input.

---

## 🛠️ Tech Stack

SuperTerminal is built using modern, light-weight, and highly-performant tools:

- **Core Language**: [Python 3.8+](https://www.python.org/)
- **LLM Provider**: [Google Gemini](https://ai.google.dev/) via `google-genai`
- **Configuration**: User-level `.env` storage with `python-dotenv`

---

## 🏗️ Architecture

SuperTerminal follows a focused Gemini-powered command translation flow:

```
                  ┌────────────────────────────────────────┐
                  │          Terminal Interface            │
                  │       (Interactive Python CLI)         │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │            Context Collector           │
                  │  (OS, Shell, CWD, Installed Tools)     │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │            Execution Planner           │
                  │       (Validation & Safety Checks)     │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │          Orchestration Engine          │
                  │       (google-genai).                  │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │          Google Gemini API             │
                  │        (Cloud Model Provider)          │
                  └────────────────────────────────────────┘
```

1. **Terminal Interface**: Runs the interactive `SuperTerminal (...) >` prompt and accepts natural language input.
2. **Context Collector**: Resolves OS, shell, current directory, and available local CLI tools.
3. **Execution Planner**: Classifies generated commands as read-only or modifying.
4. **Gemini Translator**: Sends the user intent and local context to Google Gemini and receives one shell command.
5. **Safety Gate**: Runs read-only commands immediately; places modifying commands on the next editable prompt line for user approval.

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher installed on your system.
- A Gemini API key from https://aistudio.google.com/apikey.

On first launch, SuperTerminal asks for your Gemini API key and saves it to your user config directory. You can also set `GEMINI_API_KEY` in your environment to override the stored key.

### Installation

Simply install it as a python package
```bash
pip install git+https://github.com/Hassaan9651/Super_Terminal.git
```

for updating to latest version use ```--upgrade``` flag
```bash
pip install --upgrade git+https://github.com/Hassaan9651/Super_Terminal.git
```

and run using:
```bash
   superterminal
```
or
```bash
   super
```

### Development Setup
To clone the repository and run it locally:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/SuperTerminal.git
   cd SuperTerminal
   ```

2. **Install the package locally**:
   ```bash
   pip install -e .
   ```

3. **Run SuperTerminal**:
   ```bash
   superterminal
   ```
   The first run prompts for your Gemini API key and stores it for future sessions.

---

## 💡 Usage

Start the SuperTerminal interactive session:
```bash
superterminal
```

You can also use the short alias:
```bash
super
```

Example:
```
SuperTerminal (/Users/me/project) > find all csv files in downloads
```

Natural language is the default. If you want to run a shell command directly, prefix it with `!`:

```text
SuperTerminal (/Users/me/project) > !git status
```

Read-only generated commands run immediately. Modifying generated commands are placed on an editable prompt line with `!` in front, so it is obvious that the line is now a real shell command. You can review, change, and press Enter yourself.

### 🎤 Voice Input

Voice support is installed automatically with the package. On an existing
install, upgrade first so the `supervoice` command and its dependencies are
present:
```bash
pip install --upgrade git+https://github.com/Hassaan9651/Super_Terminal.git
# or in a local checkout:
pip install -e .
```

Start SuperTerminal in voice mode:
```bash
supervoice
# equivalent: super --voice
```

A small floating mic button appears on screen (bottom-right, draggable):

- **Hold** the button, speak your command, and **release**. Your speech is translated straight into a shell command in a single Gemini call.
- Read-only commands run immediately as `!command`; modifying commands are placed on the prompt as an editable `!command` line and wait for **you** to press Enter — the same safety gate as typed input.
- If you were mid-typing when the result arrives, it is inserted into your line without auto-submitting.

Notes:
- On **macOS**, the first recording triggers the system microphone permission prompt for your terminal app (Terminal/iTerm2). If nothing is heard, check *System Settings → Privacy & Security → Microphone*.
- Plain `super`/`superterminal` never shows the overlay. In voice mode, missing prerequisites (`tkinter`, `sounddevice`) are reported at startup with the exact install fix, and headless/SSH sessions skip the overlay automatically — the typed prompt keeps working as before.
- If the overlay ever stops unexpectedly, the notice includes the path of a diagnostic log (`voice-overlay.log` in the SuperTerminal config directory) with the full error.

### Examples

**Simple read-only query**
```text
SuperTerminal (/Users/me/project) > show me all python files in this folder
```
Possible command:
```bash
find . -name "*.py"
```

**Modifying command**
```text
SuperTerminal (/Users/me/project) > make a new folder called notes
```
Possible editable command:
```bash
!mkdir notes
```

**Hard natural query**
```text
SuperTerminal (/Users/me/project) > find every log file bigger than 10mb and move them into an archive folder
```
Possible editable command:
```bash
!mkdir -p archive && find . -type f -name "*.log" -size +10M -exec mv {} archive/ \;
```

**Hard natural query with imperfect wording**
```text
SuperTerminal (/Users/me/project) > compress all jsn files frm downloads modified yestday into backup.zip
```
Possible editable command:
```bash
!find ~/Downloads -name "*.json" -mtime -2 -mtime +0 -print0 | xargs -0 zip backup.zip
```

---

## 🤝 Contribution Guidelines

We welcome contributions from the community! To get started:

1. **Fork** the repository and create your feature branch: `git checkout -b feature/amazing-feature`.
2. Ensure you have installed the dev dependencies and run **linters/formatters**:
   ```bash
   black .
   flake8 .
   ```
3. Add tests for your code. Run the test suite:
   ```bash
   pytest
   ```
4. Commit your changes with descriptive messages: `git commit -m 'feat: add offline llama3 support'`.
5. Push to the branch: `git push origin feature/amazing-feature`.
6. Open a **Pull Request** detailing your changes.

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a PR.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
