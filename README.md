# agent-tools

Reusable deterministic tools for AI agents and humans.

`agent-tools` is a collection of small, composable utilities intended to be called by AI coding agents, autonomous agents, shell scripts, or directly by a human.

The goal is to keep operational logic outside of any individual application repository and outside of agent-specific configuration such as `.claude`, `.codex`, or Hermes configuration.

Instead, tools live here behind stable interfaces—primarily command-line interfaces—so multiple agents can use the same implementation.

## Why this repository exists

AI agents are increasingly useful for tasks that extend beyond writing code:

- creating and updating Jira tickets
- interacting with GitHub
- inspecting repositories
- summarizing project activity
- managing notes and documentation
- querying engineering systems
- preparing reports
- automating repeatable workflows

It is tempting to implement this logic separately for each agent:

```text
Claude-specific Jira tooling
Codex-specific Jira tooling
Hermes-specific Jira tooling
```

That creates duplication and couples useful automation to a particular agent platform.

`agent-tools` instead provides a shared deterministic layer:

```text
             ┌───────────────┐
             │  agent-tools  │
             └───────┬───────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
     Claude        Codex         Hermes
       │             │             │
       └─────────────┴─────────────┘
```

Agents reason about **what should be done**.

The tools provide reliable implementations for **doing it**.

## Design principles

### Agent agnostic

Tools should not depend on a particular AI agent or model.

Claude, Codex, Hermes, OpenClaw, shell scripts, CI jobs, and humans should all be able to invoke the same underlying functionality.

### CLI first

Capabilities should generally be exposed as ordinary command-line tools.

For example:

```bash
jira-sync validate ./tickets
jira-sync plan ./tickets
jira-sync push ./tickets
```

A stable CLI makes tools easy to invoke from:

- AI agents
- shell scripts
- CI/CD
- cron jobs
- Python subprocesses
- MCP wrappers
- humans

### Deterministic where possible

LLMs are useful for interpretation, planning, and generation.

They should not be required for deterministic operations such as:

- API calls
- validation
- synchronization
- parsing
- file transformations
- state tracking

Where possible, tools should provide explicit inputs, predictable outputs, and clear error behavior.

### Human-in-the-loop by default

Potentially destructive or externally visible actions should normally support a preview or planning stage.

For example:

```bash
jira-sync plan ./tickets
```

before:

```bash
jira-sync push ./tickets
```

Agents should be able to inspect a proposed action before executing it.

### Idempotent operations

Running the same command repeatedly should not unintentionally create duplicate resources or corrupt state.

Tools should maintain stable identifiers where appropriate.

### Local configuration, shared implementation

Reusable behavior belongs in this repository.

Project-specific configuration belongs with the project.

Personal credentials and secrets belong outside both.

For example:

```text
~/Code/agent-tools/
    reusable implementations

~/.config/agent-tools/
    personal configuration and credentials

~/Code/my-project/.ai-tools.toml
    project-specific configuration

~/Code/my-project/tickets/
    project data
```

### Easy to wrap with MCP

CLI tools should remain useful independently of MCP.

Where an MCP interface is valuable, it should ideally wrap the same underlying Python implementation rather than duplicate business logic.

Conceptually:

```text
                    ┌── CLI
Python library ─────┤
                    └── MCP server
```

## Repository structure

The expected structure is:

```text
agent-tools/
├── README.md
├── pyproject.toml
├── src/
│   └── agent_tools/
│       ├── jira_sync/
│       ├── github/
│       ├── notes/
│       ├── research/
│       └── ...
├── tests/
├── docs/
└── examples/
```

Not every directory will necessarily exist initially.

New tools should be added as concrete use cases emerge rather than speculatively building a large framework.

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd agent-tools
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the package in editable mode:

```bash
pip install -e .
```

For development:

```bash
pip install -e '.[dev]'
```

Run tests:

```bash
pytest
```

## Available tools

### `jira-sync`

Synchronize locally defined Markdown tickets with Jira.

Typical workflow:

```bash
jira-sync validate ./tickets
jira-sync plan ./tickets
jira-sync push ./tickets
```

`jira-sync` supports:

- Jira issues defined as Markdown
- YAML front matter
- Jira issue creation
- Jira issue updates
- Markdown-to-Atlassian Document Format conversion
- local symbolic ticket IDs
- parent/child relationships
- Jira key write-back
- validation
- dry-run planning
- machine-readable JSON output for validation, planning, and push results
- idempotent synchronization

Example ticket:

```markdown
---
id: agent-observability
type: Story
priority: High
labels:
  - agents
  - observability
---

# Add agent observability

Instrument agent execution so runs can be inspected and debugged.

## Acceptance Criteria

- Each run creates a trace
- Individual workflow nodes appear as spans
- Token usage is captured
- Model latency is recorded
```

Once created in Jira, `jira-sync` records the Jira key in the front matter:

```yaml
jira_key: ENG-123
```

Future pushes update `ENG-123` rather than creating another issue.

Agents and automation can inspect a plan without parsing terminal tables:

```bash
jira-sync validate ./tickets --json
jira-sync plan ./tickets --offline --json
jira-sync push ./tickets --yes --json
```

See the Jira-specific documentation for configuration and usage details.

## Project configuration

Individual repositories may provide an `.ai-tools.toml` file.

Example:

```toml
[jira]
project = "ENG"
ticket_directory = "tickets"
```

This allows a project to describe how shared tools should operate without embedding tool implementations in the project itself.

For example:

```text
my-project/
├── .ai-tools.toml
├── src/
├── tests/
└── tickets/
    ├── epic-platform.md
    ├── story-observability.md
    └── story-evals.md
```

An agent working inside `my-project` can use the shared `jira-sync` installation while project-specific information remains local to `my-project`.

## Configuration and secrets

Secrets should never be committed to this repository.

Credentials should be provided through environment variables, the operating system credential store, or another secret-management system.

For Jira, for example:

```bash
export JIRA_BASE_URL='https://example.atlassian.net'
export JIRA_EMAIL='user@example.com'
export JIRA_API_TOKEN='...'
```

Files such as the following should not be committed:

```text
.env
credentials.env
tokens.json
```

An `.env.example` file may be provided to document supported variables.

## Using tools from AI agents

An agent should generally invoke tools in the same way a human would.

For example:

```text
1. Read and edit tickets in ./tickets.
2. Run `jira-sync validate ./tickets`.
3. Fix any validation errors.
4. Run `jira-sync plan ./tickets`.
5. Review the proposed changes.
6. Run `jira-sync push ./tickets` only when appropriate.
```

This is preferable to giving each agent its own implementation of Jira synchronization.

Agent-specific configuration should contain only the instructions necessary to discover and invoke the tool.

For example:

```text
Claude skill ───────┐
Codex instructions ─┼──► jira-sync
Hermes tool config ─┘
```

## Future tools

Potential future capabilities include:

```text
jira-sync
github-summary
repo-health
release-summary
pr-review-context
engineering-digest
notes-link
research-ingest
```

These names are illustrative rather than a roadmap.

Tools should be added when a recurring workflow benefits from a reliable, reusable implementation.

## When to create a new tool

A good candidate for `agent-tools` usually has several of these properties:

- useful across multiple repositories
- useful to multiple agents
- involves an external API or system
- repeated frequently
- benefits from deterministic behavior
- should be independently testable
- has a reasonably stable interface
- should not depend on application-specific code

A one-off script used by a single project usually belongs in that project's repository instead.

## Development guidelines

New tools should generally:

- have clear CLI help
- support safe preview/dry-run behavior where relevant
- return useful exit codes
- provide actionable errors
- avoid hidden side effects
- keep external integrations behind small interfaces
- be unit-testable without requiring live external services
- avoid agent-specific dependencies
- document configuration and credentials
- include tests for core behavior

Prefer small tools with clear contracts over a large general-purpose automation framework.

## Philosophy

The repository follows a simple division of responsibility:

```text
AI agent:
    reason
    interpret
    decide
    generate

agent-tools:
    validate
    transform
    synchronize
    execute
    persist
```

The boundary will not always be absolute, but it is a useful default.

Agents are good at handling ambiguity.

Software is good at enforcing invariants.

`agent-tools` exists to make those two capabilities work together.
