# SuperTerminal 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

**SuperTerminal** is an AI-powered terminal assistant designed to bridge the gap between natural language and the command line. It translates complex tasks into executable shell commands, explains system outputs, troubleshoots errors in real-time, and automates multi-step terminal workflows—all without leaving your shell.

---

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
3. **Install the package locally**:
   ```bash
   pip install -e .
   ```

4. **Run SuperTerminal**:
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

Read-only commands run immediately. Modifying commands are placed on the next editable prompt line so you can review, change, and press Enter yourself.

### Examples

**Simple read-only query**
```text
SuperTerminal (/Users/me/project) > show me all python files in this folder
```
Possible command:
```bash
find . -name "*.py"
```
SuperTerminal (/Users/me/project) > find all csv files in downloads
```

Read-only commands run immediately. Modifying commands are placed on the next editable prompt line so you can review, change, and press Enter yourself.

**Modifying command**
```text
SuperTerminal (/Users/me/project) > make a new folder called notes
```
Possible editable command:
```bash
mkdir notes
```

**Hard natural query**
```text
SuperTerminal (/Users/me/project) > find every log file bigger than 10mb and move them into an archive folder
```
Possible editable command:
```bash
mkdir -p archive && find . -type f -name "*.log" -size +10M -exec mv {} archive/ \;
```

**Hard natural query with imperfect wording**
```text
SuperTerminal (/Users/me/project) > compress all jsn files frm downloads modified yestday into backup.zip
```
Possible editable command:
```bash
find ~/Downloads -name "*.json" -mtime -2 -mtime +0 -print0 | xargs -0 zip backup.zip
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
