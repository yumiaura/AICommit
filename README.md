# 🤖 aicommit

> **AI commit messages from your local LLM.**
> Reads `git diff --staged`, asks Ollama for a clean Conventional Commit, commits.

Everything runs offline. No API keys, no data leaves the box.

---

## ✨ Features

- 📝 Generates **Conventional Commit** messages from staged changes
- 🤖 Powered by a **local LLM** via Ollama (or `llama-cpp-python`)
- ✍️ Opens the proposal in `$EDITOR` for a quick approval / edit / regenerate loop
- 📓 `changelog` subcommand: summarizes a tag range into a `CHANGELOG.md` entry
- 🔌 Installs as a `git` subcommand — call it as `git aicommit`

---

## 🚀 Quick start

```bash
# 1. install a model in Ollama (any chat-instruct model works)
ollama pull qwen2.5-coder:7b

# 2. install aicommit straight from GitHub
pip install git+https://github.com/yumiaura/AICommit

# 3. stage and let it write the message
git add -A
git aicommit
```

> A demo asciicast lives in [`docs/demo.cast`](docs/demo.cast) — open it
> with `asciinema play docs/demo.cast` or paste into asciinema.org.

Sample interaction:

```text
─── proposed message ────────────────────────────────
fix(parser): handle empty input gracefully

- return [] instead of raising on whitespace-only files
- add regression test for the empty-file case
─────────────────────────────────────────────────────
[ Enter = commit · e = edit · r = regenerate · q = quit ]
```

Changelog mode:

```bash
git aicommit changelog v0.4.0..HEAD --out CHANGELOG.md
```

---

## ⚙️ Configuration

`~/.config/aicommit/config.toml`:

```toml
[llm]
backend = "ollama"           # ollama | llama-cpp
model   = "qwen2.5-coder:7b"
url     = "http://localhost:11434"
temperature = 0.2

[commit]
style          = "conventional"   # conventional | plain
max_subject_len = 72
include_body    = true
```

Environment variables override the file (`AICOMMIT_MODEL=...`), and CLI
flags override env. Per-repo overrides go in `<repo>/.aicommit.toml`.

Useful flags:

```text
aicommit [--model M] [--url URL] [--temperature T] [--style {conventional,plain}]
         [--no-body] [--review] [--review-only] [--print] [-y] [--debug]
aicommit changelog <rev-range> [--out CHANGELOG.md]
```

---

## 📦 Stack

- `ollama` HTTP API (or `llama-cpp-python` for in-process inference)
- `subprocess` to call `git`
- `argparse` + `rich` for the CLI
- `tomllib` (Python 3.11+) for config

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md).

---

## 📄 License

MIT (planned).

Author: [@yumiaura](https://github.com/yumiaura)
