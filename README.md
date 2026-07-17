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
- **Context-Aware Recommendations**: Understands your current OS, shell (bash, zsh, powershell), directory context, and command history to provide tailored assistance.
- **Real-Time Error Troubleshooting**: Automatically captures stderr from failed commands and explains the root cause along with a one-click fix.
- **Interactive Multi-Step Workflows**: Guides you through complex operations (e.g., setting up Docker environments, configuring CI/CD pipelines) using interactive prompt menus.
- **Safety First & Verification**: Dry-run preview mode lets you inspect, edit, or reject generated commands before execution.
- **Extensible Agent Integration**: Connects to your favorite LLM providers (OpenAI, Anthropic, Ollama, Google Gemini) using secure API keys or local configurations.

---

## 🛠️ Tech Stack

SuperTerminal is built using modern, light-weight, and highly-performant tools:

- **CLI Framework**: [Typer](https://typer.tiangolo.com/) & [Rich](https://rich.readthedocs.io/) (for beautiful, interactive terminal user interfaces)
- **Core Language**: [Python 3.8+](https://www.python.org/)
- **LLM Orchestration**: [LiteLLM](https://github.com/BerriAI/litellm) / [LangChain](https://github.com/langchain-ai/langchain) (for seamless switching between OpenAI, Anthropic, Gemini, and local LLMs)
- **Local LLM Support**: [Ollama](https://ollama.com/) integration
- **Configuration & State**: [Pydantic Settings](https://docs.pydantic.dev/) & YAML configurations

---

## 🏗️ Architecture

SuperTerminal follows a modular, agentic workflow architecture:

```
                  ┌────────────────────────────────────────┐
                  │          Terminal User Interface       │
                  │             (Typer & Rich UI)          │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │            Context Collector           │
                  │   (OS, Shell, Current Directory, CWD)  │
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
                  │               LLM Agent                │
                  │   (LiteLLM / Prompt Template Engine)   │
                  └──────┬──────────────────────────┬──────┘
                         │                          │
                         ▼                          ▼
            ┌────────────────────────┐  ┌────────────────────────┐
            │     Cloud LLM APIs     │  │   Local LLM (Ollama)   │
            │   (OpenAI, Anthropic,  │  │ (Llama 3, Codegemma)   │
            │     Gemini, etc.)      │  │                        │
            └────────────────────────┘  └────────────────────────┘
```

1. **Terminal User Interface**: Renders prompts, interactive selections, syntax highlighting, and progress animations.
2. **Context Collector**: Resolves local system information dynamically (e.g., detecting if running under Windows PowerShell or macOS Zsh) to prevent invalid commands.
3. **Execution Planner**: Safeguards the user by scanning generated commands for dangerous operations (e.g., recursive deletes on system folders) and prompts for confirmation.
4. **LLM Agent**: Translates prompts, handles fallback strategies, parses syntax, and generates structured command schemas.

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

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

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

---

## 🗺️ Future Roadmap

- [ ] **Shell Alias Integration**: Native shell alias hooks to execute commands instantly with a hotkey trigger.
- [ ] **Local Offline Mode**: Optimized offline support using tiny, fast quantized coding models running locally.
- [ ] **Collaborative Terminal Sessions**: Securely share terminal screens and AI-guided explanations with teammates.
- [ ] **Custom System Agents**: Define customized scripts and context rules inside `.superterminal.yaml` files.
- [ ] **Telemetry & CLI Analytics**: Local analytics dashboard to review saved time, executed commands, and error logs.

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
