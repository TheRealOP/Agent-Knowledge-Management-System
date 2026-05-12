# AKMS Integration Guide for Gemini and Codex

Here is how you can deeply integrate the Agent Knowledge Management System (AKMS) with the Gemini CLI (and Codex). AKMS already has built-in support for MCP and can wrap CLIs like Gemini directly.

## 1. Using Gemini as the LLM inside AKMS (Provider)

You don't need a separate API key. AKMS has a `cli_subprocess` provider that can drive the Gemini CLI in headless mode (`gemini -p`). 

Add this to your `akms_config.yaml`:

```yaml
providers:
  gemini_cli:
    # Uses the CLISubprocessProvider to wrap your existing Gemini CLI auth
    models:
      - gemini-2.5-pro
    tmux_pane: akms-gemini # Optional: tail -f ~/.akms/panes/akms-gemini.log to watch it think

  codex_cli:
    models:
      - gpt-5-codex

agent_assignments:
  expert:
    provider: gemini_cli
    model: gemini-2.5-pro
  librarian:
    provider: codex_cli  # You can mix and match!
    model: gpt-5-codex
```

## 2. Using AKMS as an MCP Tool for Gemini

AKMS has a built-in MCP server that exposes tools like `search_graph`, `ask_section`, and `ingest_document`.

1. **Install the MCP dependencies:**
   Inside the AKMS directory, run:
   ```bash
   pip install -e ".[mcp]"
   ```

2. **Register the server in Gemini:**
   Add this to your `~/.gemini/settings.json` (or your project's `.gemini/settings.json`):
   ```json
   {
     "mcpServers": {
       "akms": {
         "command": "akms-mcp",
         "args": [],
         "env": {
           "AKMS_CONFIG": "/path/to/your/akms_config.yaml"
         }
       }
     }
   }
   ```
3. Run `/mcp reload` in your Gemini session. Gemini will now automatically use the knowledge graph when you ask it domain questions.

## 3. Creating Custom Slash Commands

You can create custom slash commands (e.g., `/akms`) for Gemini or Codex to quickly run AKMS CLI tools.

### For Gemini
Create a file at `~/.gemini/commands/akms.toml`:

```toml
description = "Query the AKMS Knowledge Graph"
prompt = "Please run the following AKMS command and summarize the output for me: !{akms {{args}}}"
```
*Usage:* Type `/akms search "consensus algorithms"` or `/akms ask "distributed-systems" "How does Raft work?"`

### For Codex
Codex (like Claude Code or other advanced CLIs) typically supports similar plugin architectures or relies on `.codex/` system prompts. However, if it supports shell execution skills, you can simply instruct it in your `AGENTS.md` to use the `akms` binary directly, as the CLI is the universal interface.