# GitKritik2

**AI-powered, context-aware code review CLI and CI agent for Git.**
Built on [LangGraph](https://github.com/langchain-ai/langgraph), GitKritik brings multi-agent reasoning to your code changes, understanding symbols defined in other files (currently Python-only via Jedi) to provide deeper insights. It runs directly from your terminal or integrates into your CI pipeline.

---

## 🚀 Features

-   ✅ **Native Git Integration:** Use directly via `git kritik`.
-   🧠 **Multi-Agent Architecture:** Modular agents for Style, Bugs, Design/Architecture, Context Gathering (ReAct), and Summarization.
-   🐍 **Python Context Awareness:** ReAct agent uses [Jedi](https://jedi.readthedocs.io/) to fetch definitions of imported Python symbols from other project files, informing bug/design analysis.
-   🤖 **Broad LLM Support:** Works with OpenAI (GPT models), Anthropic (Claude models), Google (Gemini models), and local LLMs via Ollama.
-   🖥️ **Rich CLI Output:** Uses `rich` for formatted diffs and inline comments directly in your terminal, highlighting agent contributions.
-   ⚙️ **CI Integration:** Seamlessly integrates with GitHub Actions & GitLab CI to post inline and summary comments on PRs/MRs.
-   🛡️ **Robust Configuration:** Configure via `.kritikrc.yaml` and `.env`, with environment variables taking precedence.
-   📦 **Reproducible & Extensible:** Built with Poetry for dependency management, Pydantic for data validation, and LangGraph for workflow orchestration.
-   🔍 **Observability:** Easily integrate with [LangSmith](https://smith.langchain.com/) for tracing and debugging agent behavior.

---

## 🧰 Installation & Reproducibility

Requires Python 3.10+. We use [Poetry](https://python-poetry.org/) for dependency management to ensure reproducible environments.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/preslaff/gitkritik2.git # Use your actual repo URL
    cd gitkritik2
    ```
2.  **Install Dependencies using Poetry:**
    ```bash
    # Install Poetry if you haven't already (https://python-poetry.org/docs/#installation)
    pipx install poetry

    # Install project dependencies locked in poetry.lock
    poetry install --no-root
    ```
    *Using `poetry install` guarantees you install the exact versions of dependencies specified in `poetry.lock`, ensuring others can reproduce your environment.*

3.  **(Optional) Activate Virtual Environment:**
    ```bash
    poetry shell
    ```
    *This activates the virtual environment managed by Poetry, making the `kritik` command directly available.*

This makes the `git kritik` command available either directly (if using `poetry shell`) or via `poetry run kritik`. The installation via Poetry handles the creation of the necessary command-line entry points.

---

## 🧑‍💻 Usage

Ensure you are inside your target Git repository.

### 🔍 Local Review

Review changes locally before committing or pushing.

```bash
# Activate environment (if not already done)
# poetry shell

# Review only unstaged changes vs the index
git kritik -u

# Review only staged changes vs the merge-base with origin/main
# (This is the default if no flags are given and staged files exist)
git kritik

# Review all local changes (staged + unstaged) vs HEAD
git kritik -a

# Show inline comments in the terminal output (in addition to summary)
git kritik -i

# Combine flags (e.g., review unstaged with inline comments)
git kritik -u -i
```

*(Note: Side-by-side view (`-s`) is currently experimental and may fall back to unified view).*

### 🤖 In CI (GitHub Actions Example)

Add this to your `.github/workflows/your_workflow.yml`:

```yaml
name: AI Code Review

on:
  pull_request:

jobs:
  ai_review:
    runs-on: ubuntu-latest
    permissions:
      contents: read # Need read access to checkout
      pull-requests: write # Need write access to post comments/reviews
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        # Fetch full history for accurate diffing against merge-base
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11' # Match your project's requirement

      - name: Install Poetry
        run: pipx install poetry

      - name: Install Dependencies
        # Use --sync if you want to ensure only lock file deps are present
        run: poetry install --no-root --sync

      - name: Run GitKritik Review
        # --ci enables CI mode (env var detection)
        # --inline enables posting inline comments to the PR/MR
        run: poetry run kritik --ci --inline
        env:
          # Required for posting comments/reviews
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # Required API keys for your configured LLM provider
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          # Optional: LangSmith tracing
          LANGCHAIN_TRACING_V2: "true"
          LANGCHAIN_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          LANGCHAIN_PROJECT: "GitKritik-${{ github.repository }}" # Example project name
```

This configuration ensures a consistent environment using Poetry and posts review comments directly to the GitHub Pull Request.

*(GitLab CI setup is similar, ensure `GITLAB_TOKEN` or `CI_JOB_TOKEN` is available).*

---

## ⚙️ Configuration

Configure GitKritik via `.kritikrc.yaml` and `.env` files in your project root. Environment variables always override file settings. See example files in the repository.

-   **`.kritikrc.yaml`:** Configure `platform`, `strategy`, `llm_provider`, `model`, `temperature`, `max_tokens`.
-   **`.env`:** Store sensitive API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) and platform tokens (`GITHUB_TOKEN`, `GITLAB_TOKEN`). **Do not commit `.env`!**

---

## 🧠 Architecture (Using LangGraph)

GitKritik employs a stateful graph architecture orchestrated by LangGraph:

1.  **Setup:** Initialize state, resolve Git/CI context.
2.  **Diffing:** Detect changed files and prepare context (diffs, file content).
3.  **Context Agent (ReAct):** Analyzes Python code changes, uses **Jedi** to find definitions of imported project symbols, enriching the context.
4.  **Review Agents:** Specialized agents (Bug, Design, Style) analyze changes using the enriched context and LLM calls. Comments are filtered to match added lines in the diff.
5.  **Summarization:** An agent generates a high-level summary.
6.  **Output:** Results are merged, formatted, and either displayed locally via `rich` or posted to the configured platform (GitHub/GitLab).

---

## 🛠️ Future Work & Enhancements

-   **Multi-Language Context Agent (LSP):**
    -   Implement a new LangChain tool leveraging the **Language Server Protocol (LSP)**.
    -   Integrate with standard LSP servers (e.g., `gopls`, `typescript-language-server`, `clangd`, `jdtls`, `OmniSharp`, `solargraph`).
    *   This will enable context-aware analysis (`get_symbol_definition`) for languages beyond Python (Go, TS/JS, C/C++, Java, C#, Ruby).
    *   Requires user installation of relevant LSP servers and potentially configuration within GitKritik.
-   **Improved ReAct Tool Calling:** Enhance the reliability of the ReAct agent's ability to format tool inputs correctly, potentially by using native LLM tool-calling features (e.g., OpenAI Functions/Tools) instead of text parsing.
-   **More Robust Diff Parsing:** Ensure maximum accuracy in mapping LLM comments to specific changed lines using libraries like `unidiff`.
-   **Configuration Validation:** Add stricter validation for `.kritikrc.yaml` contents.
-   **Agent Tuning:** Fine-tune prompts and logic for specific agent types.
-   **Additional Agents:** Explore agents for security vulnerabilities, documentation consistency, etc.
-   **Caching:** Implement caching for LLM calls or fetched definitions to improve performance and reduce costs.

---

## 🤝 Contributing

Contributions are highly welcome! Please see `CONTRIBUTING.md` (if available) or open an issue/PR to discuss improvements. Using Poetry for development is recommended for consistency.

---

## 📄 License

MIT © 2024 Preslav Apostolov <preslaff@gmail.com>
```

**Key Updates:**

*   Clarified the Python-only context awareness (Jedi).
*   Added a dedicated "Installation & Reproducibility" section emphasizing Poetry.
*   Updated the CI example with Poetry usage and clearer env var explanations.
*   Explicitly listed the LSP integration under "Future Work & Enhancements", detailing the goal and requirements.
*   Added other potential future work items like improved ReAct, caching, etc.
*   Slightly refined the Architecture description.
*   Updated license owner and year.

This README provides a clearer picture of the current state, installation process, and future direction, including the significant LSP enhancement plan.