**AI-powered code review CLI and CI agent for Git.**  
Built on [LangGraph](https://github.com/langchain-ai/langgraph), GitKritik brings multi-agent reasoning to your pull requests, commit diffs, and full files — all from your terminal or CI.

---

## 🚀 Features

- ✅ Full Git integration as a native extension: `git kritik`
- 🧠 Modular multi-agent architecture (Style, Bugs, Context, Summary)
- 🤖 Supports OpenAI, Claude, Gemini, and local LLMs
- 🖥️ Rich CLI output with diffs and inline comments
- ⚙️ GitHub & GitLab CI support (posts inline & summary comments)
- 📦 Clean Poetry + Pydantic setup for extensibility

---

## 🧰 Installation

### 📦 Using Poetry (recommended)

```bash
poetry install
```

### 🐍 Or using pip (editable mode)

```bash
pip install -e .
```

This makes `git kritik` available as a Git extension.

---

## 🧑‍💻 Usage

### 🔍 Local Review (Before Commit)

```bash
git kritik --unstaged        # Review unstaged code
git kritik --all             # Review all changes
git kritik --side-by-side    # Show rich diff layout
```

### 🤖 In CI (GitHub/GitLab)

```yaml
# .github/workflows/review.yml
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run GitKritik
        run: git kritik --ci
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This posts:
- ✅ Inline comments (GitHub: "Files Changed", GitLab: "Changes")
- ✅ Summary comment (GitHub: "Conversation", GitLab: "Overview")

---

## ⚙️ Configuration

### 🔧 `.kritikrc.yaml`

```yaml
platform: github
strategy: hybrid
model: gpt-4
llm_provider: openai
```

### 🔐 `.env`

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant...
GEMINI_API_KEY=AIza...
GITHUB_TOKEN=ghp_...
```

GitKritik auto-detects CI environment variables like:
- `GITHUB_ACTIONS`
- `GITLAB_CI`

---

## 🧠 Architecture

| Phase         | Node                     |
|---------------|--------------------------|
| Init          | `init_state`             |
| CI Detect     | `detect_ci_context`      |
| Git Diff      | `detect_changes`         |
| Context Prep  | `prepare_context`        |
| Agents        | `style_agent`, `bug_agent`, `context_agent`, `summary_agent` |
| Post-process  | `merge_results`, `format_output` |
| Output        | `post_inline`, `post_summary` or CLI display |

---

## 🤝 Contributing

Want to add a new agent or support more models?  
Feel free to fork, PR, or open a discussion!

---

## 📄 License

MIT © 2024 [preslaff@gmail.com]