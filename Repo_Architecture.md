# Repository for AI CLI Tools

(response from ChatGPT, during creation of jira-sync tool)

A dedicated repository such as:

```text
~/Code/ai-tools
```

is a good starting point.

The reason is architectural: these are not really “project scripts.” They are becoming a **personal/internal tool layer for agents**. You want Hermes, Codex, Claude Code, and potentially other agents to call the same stable utilities without duplicating implementation across repos.

I’d structure it more deliberately than a loose scripts folder, though:

```text
~/Code/ai-tools/
├── README.md
├── pyproject.toml
├── src/
│   └── ai_tools/
│       ├── jira_sync/
│       │   ├── cli.py
│       │   ├── config.py
│       │   ├── models.py
│       │   ├── markdown.py
│       │   ├── adf.py
│       │   ├── planner.py
│       │   └── jira/
│       │       └── rest.py
│       │
│       ├── github/
│       ├── slack/
│       ├── research/
│       └── notes/
│
├── tests/
│   └── jira_sync/
│
├── docs/
│   └── jira-sync.md
│
└── examples/
    └── jira-tickets/
```

The key design idea would be:

```text
Agents
  │
  ├── Hermes
  ├── Codex
  ├── Claude Code
  └── others
       │
       ▼
   ai-tools
       │
       ├── jira-sync
       ├── github utilities
       ├── notes tooling
       ├── research tooling
       └── future integrations
```

I would **not** make each tool its own repository yet. That becomes annoying surprisingly quickly. A monorepo is a better fit while these are primarily tools for your own workflows.

### CLI boundaries matter more than agent integration

I would design every useful capability first as an ordinary CLI:

```bash
jira-sync plan ./tickets
jira-sync push ./tickets

github-summary --repo foo/bar
notes-link ~/notes/today.md
```

Then agents simply execute those commands.

That gives you a stable interface independent of whichever agent happens to be fashionable six months from now:

```text
Claude Code ─┐
Codex        ├── subprocess / shell ──► jira-sync
Hermes       ┤
OpenClaw     ┘
```

Later, if one of these capabilities deserves MCP exposure, you can wrap the **same underlying Python library**:

```text
                 ┌── CLI
ai_tools.jira ───┤
                 └── MCP server
```

rather than implementing Jira logic again inside an MCP server.

### I would also separate tools from credentials/config

The repository should contain code, but not your Jira credentials or project-specific configuration.

For example:

```text
~/.config/ai-tools/
├── config.toml
└── credentials.env
```

with something like:

```toml
[jira]
base_url = "https://example.atlassian.net"
default_project = "AI"

[jira.projects.remedy]
project = "REM"

[jira.projects.thincalc]
project = "THIN"
```

And credentials through environment variables or eventually a secret manager:

```bash
JIRA_EMAIL=...
JIRA_API_TOKEN=...
```

The repo can contain:

```text
.env.example
```

but never `.env`.

### Make project repos declarative

Individual projects can still contain a tiny amount of project-specific metadata.

For example:

```text
~/Code/remedy/
├── src/
├── tests/
├── tickets/
│   ├── REM-architecture.md
│   └── REM-ingestion.md
└── .ai-tools.toml
```

with:

```toml
[jira]
project = "REM"
ticket_directory = "tickets"
```

Then from inside any repository:

```bash
jira-sync plan
```

could automatically discover `.ai-tools.toml`.

That is preferable to teaching the global tool about every repository.

So the responsibilities become:

```text
~/Code/ai-tools
    reusable behavior

~/.config/ai-tools
    personal/global configuration + credentials

~/Code/some-project/.ai-tools.toml
    project-specific configuration

~/Code/some-project/tickets/
    actual Jira ticket definitions
```

That separation will scale well.

### One naming suggestion

I would consider naming the repository something slightly broader than `AI-tools`.

My preference would probably be:

```text
~/Code/agent-tools
```

because these aren't necessarily AI implementations themselves—they're **capabilities exposed to agents**.

Other reasonable names:

```text
agent-tools
agent-kit
agent-utils
automation-tools
personal-tooling
```

I slightly prefer **`agent-tools`** because its purpose is immediately obvious:

> reusable deterministic tools intended to be invoked by AI agents or humans.

Then your Python package could still be:

```python
agent_tools.jira
agent_tools.github
agent_tools.notes
```

and your commands remain friendly:

```bash
jira-sync
github-summary
repo-health
```

### One thing I would avoid

I would **not** put these into:

```text
~/.claude/
~/.codex/
~/.hermes/
```

except for tiny adapter/config files.

Those directories should contain things specific to that particular harness:

```text
Claude skill → calls jira-sync
Codex instruction → calls jira-sync
Hermes tool definition → calls jira-sync
```

The implementation itself stays neutral.

That prevents this:

```text
Claude Jira implementation
Codex Jira implementation
Hermes Jira implementation
```

and gives you:

```text
              jira-sync
             /    |    \
        Claude  Codex  Hermes
```

which is exactly the abstraction you want.

Given where you're heading with Hermes as a broader engineering-management assistant and with multiple coding agents, I think you're effectively starting to build a small **personal agent platform**. Treating deterministic tools as a separate reusable layer now will save a lot of duplication later. 

For v1, my recommendation would therefore be:

```text
~/Code/agent-tools/
```

with `jira-sync` as the first package/tool inside it.