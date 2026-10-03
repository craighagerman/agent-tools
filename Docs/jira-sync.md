# jira-sync

`jira-sync` synchronizes Jira Cloud issues from local Markdown files.

It is designed for workflows where humans or AI agents author tickets locally, review the proposed changes, and then push those changes to Jira through a deterministic CLI.

```text
Markdown tickets
      ↓
jira-sync validate
      ↓
jira-sync plan
      ↓
human/agent review
      ↓
jira-sync push
      ↓
Jira Cloud
```

`jira-sync` is part of the `agent-tools` repository and is intended to work equally well when invoked manually or by tools such as Claude Code, Codex, Hermes, or other automation systems.

---

## Features

Version 0.1 supports:

- Jira Cloud REST API v3
- Markdown ticket files with YAML front matter
- recursive discovery of ticket files
- local validation without Jira access
- online and offline planning
- creating Jira issues
- updating existing Jira issues
- writing Jira keys back into Markdown files
- local symbolic ticket IDs
- parent/child relationships
- dependency ordering for newly-created parents and children
- Markdown-to-Atlassian Document Format conversion
- Jira labels
- priorities
- assignees by account ID
- arbitrary Jira custom fields
- per-project `.ai-tools.toml` configuration
- environment-variable credentials

The CLI deliberately does not require an LLM. It provides a deterministic execution layer that an AI agent can call.

---

# Installation

From the `agent-tools` repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Verify the installation:

```bash
jira-sync --help
```

The package requires Python 3.11 or later.

---

# Authentication

`jira-sync` currently uses Jira Cloud basic authentication with:

- your Atlassian account email
- an Atlassian API token

Set the following environment variables:

```bash
export JIRA_BASE_URL='https://your-company.atlassian.net'
export JIRA_EMAIL='you@example.com'
export JIRA_API_TOKEN='your-api-token'
```

Optionally configure a default Jira project:

```bash
export JIRA_PROJECT='ENG'
```

Do not commit API tokens to source control.

`jira-sync` intentionally does not automatically load `.env` files. Secrets should be supplied by the shell, password manager, secret manager, CI environment, or agent runtime.

---

# Project configuration

A repository that uses `jira-sync` may include an `.ai-tools.toml` file.

For example:

```toml
[jira]
project = "ENG"
ticket_directory = "tickets"
```

A project might therefore look like:

```text
my-project/
├── .ai-tools.toml
├── src/
├── tests/
└── tickets/
    ├── epic-agent-platform.md
    ├── story-observability.md
    └── task-add-metrics.md
```

When no path is supplied to `jira-sync`, the configured `ticket_directory` is used.

For example:

```bash
jira-sync validate
jira-sync plan
jira-sync push
```

With the configuration above, these commands operate on:

```text
./tickets
```

## Configuration discovery

`jira-sync` searches upward from the working path for `.ai-tools.toml`.

This means it can be invoked from inside a nested directory while still using configuration from the project root.

For example:

```text
my-project/
├── .ai-tools.toml
├── src/
│   └── some/package/
└── tickets/
```

Running the CLI from somewhere under `my-project/` can still discover the project's configuration.

## Configuration precedence

Environment variables override values from `.ai-tools.toml`.

For example:

```toml
[jira]
project = "ENG"
```

can temporarily be overridden with:

```bash
export JIRA_PROJECT='TEST'
```

---

# Ticket format

Each ticket is a Markdown file.

Metadata is supplied through optional YAML front matter and the body becomes the Jira description.

Example:

````markdown
---
id: langfuse-tracing
project: ENG
type: Story
priority: High
labels:
  - agents
  - observability
parent: agent-platform
---

# Add Langfuse tracing to agent execution

Instrument each agent execution so that it can be inspected in Langfuse.

## Acceptance Criteria

- Each invocation creates a trace
- Individual nodes appear as spans
- Token usage is captured
- Model latency is captured

## Technical Notes

```python
tracer.start_span("planner")
```
````

---

# Ticket metadata

## `id`

Optional local identifier:

```yaml
id: langfuse-tracing
```

The ID does not need to correspond to a Jira issue key.

It allows other local tickets to reference the issue before Jira has assigned a key.

For example:

```yaml
parent: agent-platform
```

where another ticket contains:

```yaml
id: agent-platform
```

Local IDs must be unique within the set of tickets being synchronized.

---

## `jira_key`

The Jira issue associated with the file:

```yaml
jira_key: ENG-123
```

If `jira_key` is absent, `jira-sync` plans to create a new issue.

If `jira_key` is present, `jira-sync` plans to update the corresponding Jira issue.

After successfully creating a new issue, `jira-sync` writes the returned Jira key into the Markdown file automatically.

For example:

```yaml
---
id: langfuse-tracing
jira_key: ENG-456
type: Story
---
```

This provides the identity required for subsequent runs to update the existing issue rather than create a duplicate.

---

## `project`

Jira project key:

```yaml
project: ENG
```

This can be omitted when a default project is supplied through either:

```toml
[jira]
project = "ENG"
```

or:

```bash
export JIRA_PROJECT='ENG'
```

Every ticket must ultimately resolve to a Jira project.

---

## `type`

Jira issue type:

```yaml
type: Story
```

Examples might include:

```yaml
type: Task
```

```yaml
type: Bug
```

```yaml
type: Epic
```

The value must correspond to an issue type available in the target Jira project.

`issue_type` is also accepted:

```yaml
issue_type: Story
```

The default is:

```yaml
Task
```

---

## `summary`

The Jira summary may be defined explicitly:

```yaml
summary: Add Langfuse tracing
```

`title` is also accepted:

```yaml
title: Add Langfuse tracing
```

Normally, however, the first level-one Markdown heading can be used:

```markdown
# Add Langfuse tracing
```

The summary is resolved in this order:

1. `summary`
2. `title`
3. first `# Heading`

At least one must exist.

When the first H1 provides the summary, that heading is removed from the Jira description so it is not duplicated.

---

## `labels`

Jira labels may be supplied as a list:

```yaml
labels:
  - agents
  - observability
```

A single string is also accepted:

```yaml
labels: observability
```

---

## `priority`

A Jira priority may be specified by name:

```yaml
priority: High
```

It is sent to Jira as:

```json
{
  "priority": {
    "name": "High"
  }
}
```

The named priority must exist in the Jira configuration.

---

## `parent`

A parent may be specified using either a Jira key or a local ticket ID.

### Existing Jira parent

```yaml
parent: ENG-101
```

### Local parent

Parent ticket:

```yaml
---
id: agent-platform
type: Epic
---

# Agent platform
```

Child ticket:

```yaml
---
id: observability
type: Story
parent: agent-platform
---

# Add observability
```

If both tickets are new, `jira-sync` creates the parent first, obtains its Jira key, and then uses that key when creating the child.

This allows locally-authored ticket trees to be created in a single push.

---

## `assignee_account_id`

A Jira assignee can be supplied using its Atlassian account ID:

```yaml
assignee_account_id: 557058:abcd1234
```

The CLI currently expects an account ID rather than an email address or display name.

---

## `fields`

Arbitrary Jira fields can be passed using the `fields` mapping.

For example:

```yaml
fields:
  customfield_10042: 5
  customfield_10401:
    value: Platform
```

These fields are merged into the Jira request.

This allows `jira-sync` to support project-specific custom fields without hard-coding them into the CLI.

`jira-sync` does not currently perform Jira field-schema discovery, so the caller is responsible for supplying values in the format expected by Jira.

---

# Extra front-matter fields

Unknown front-matter keys are also treated as Jira fields.

For example:

```yaml
---
id: example
type: Story
customfield_10042: 5
---
```

is effectively equivalent to:

```yaml
---
id: example
type: Story
fields:
  customfield_10042: 5
---
```

Using the explicit `fields:` mapping is generally recommended because it makes the distinction between `jira-sync` metadata and Jira fields clearer.

---

# Markdown descriptions

The Markdown body is converted into Jira's Atlassian Document Format (ADF) before it is sent through Jira REST API v3.

Common Markdown constructs supported by v0.1 include:

- paragraphs
- headings
- ordered lists
- unordered lists
- blockquotes
- horizontal rules
- fenced code blocks
- emphasis
- strong text
- inline code
- links

For example:

````markdown
## Acceptance Criteria

- User can authenticate
- Authentication failures are logged

> Authentication secrets must never be logged.

```python
authenticate(user)
```
````

is converted into an ADF document before transmission to Jira.

The original Markdown remains unchanged locally except when `jira-sync` adds a newly-created `jira_key`.

---

# Commands

## `validate`

Validate ticket files locally:

```bash
jira-sync validate ./tickets
```

Or, when `ticket_directory` is configured:

```bash
jira-sync validate
```

Validation does not contact Jira.

It checks conditions including:

- every ticket resolves to a Jira project
- local IDs are unique
- local parent references point to known tickets

Successful output resembles:

```text
Valid: 4 ticket(s)
```

Validation errors result in a non-zero exit code.

This command is safe for agents to run freely.

For structured results, use:

```bash
jira-sync validate ./tickets --json
```

Successful validation returns `valid: true`, ticket and error counts, and an empty `errors` array. Invalid tickets return `valid: false`, structured error messages, and exit code `1`.

---

# `plan`

Preview what synchronization would do.

## Online plan

```bash
jira-sync plan ./tickets
```

Online planning contacts Jira.

For tickets containing a `jira_key`, it verifies that the Jira issue actually exists.

A ticket without a `jira_key` becomes:

```text
CREATE
```

A ticket with an existing `jira_key` becomes:

```text
UPDATE
```

The CLI displays a table containing:

- action
- file
- issue type
- summary
- parent
- reason

Example conceptually:

```text
Action   File                         Type    Summary                  Parent          Reason
CREATE   tickets/epic.md              Epic    Agent platform                           no jira_key
CREATE   tickets/observability.md     Story   Add observability       agent-platform  no jira_key
UPDATE   tickets/evals.md             Story   Improve eval pipeline   ENG-101         existing issue ENG-205
```

Planning never modifies Jira.

---

## Offline plan

To plan without Jira credentials or network access:

```bash
jira-sync plan ./tickets --offline
```

Offline mode infers actions only from local state:

```text
jira_key missing  → CREATE
jira_key present  → UPDATE
```

It does not verify whether referenced Jira issues actually exist.

This is useful during local editing, CI validation, or when an AI agent should inspect proposed changes before being granted external-system access.

---

## JSON plan

Agents and automation can request a structured plan instead of the Rich terminal table:

```bash
jira-sync plan ./tickets --json
jira-sync plan ./tickets --offline --json
```

The JSON document contains a versioned schema, the planning mode, aggregate action counts, and one item per ticket. Each item includes its action, relative file path, local and Jira identifiers, project, issue type, summary, parent references, priority, labels, and planning reason.

```json
{
  "schema_version": 1,
  "mode": "offline",
  "summary": {"total": 2, "create": 2, "update": 0, "noop": 0},
  "items": [
    {
      "action": "CREATE",
      "file": "epic.md",
      "local_id": "agent-platform",
      "jira_key": null,
      "project": "ENG",
      "issue_type": "Epic",
      "summary": "Agent platform",
      "parent": null,
      "resolved_parent_key": null,
      "priority": "High",
      "labels": ["agents"],
      "reason": "no jira_key"
    }
  ]
}
```

JSON is written to standard output, making it safe to pipe to tools such as `jq`. Planning remains read-only. The current planner reports create or update intent; it does not yet calculate field-level diffs or semantic `NOOP` results.

---

# `push`

Apply the synchronization plan:

```bash
jira-sync push ./tickets
```

Before making changes, `jira-sync` displays totals such as:

```text
Plan: 3 create, 2 update
```

and asks:

```text
Apply this plan to Jira?
```

If confirmed, issues are created or updated one at a time.

For machine-readable results, combine `--json` with `--yes`:

```bash
jira-sync push ./tickets --yes --json
```

Requiring `--yes` prevents an interactive confirmation prompt from contaminating standard output. The JSON result includes action totals, write-back status, and one result per ticket with the final Jira key. A successful item has `status: "succeeded"`. Push is not transactional; if Jira rejects an operation, earlier operations may already have completed.

---

## Skip confirmation

For automation or for an agent that has already been authorized to execute the reviewed plan:

```bash
jira-sync push ./tickets --yes
```

or:

```bash
jira-sync push ./tickets -y
```

Because this command changes Jira state, agent workflows should generally require an explicit human approval step before using `--yes`.

---

## Disable Jira-key write-back

By default, newly-created Jira keys are written back to their Markdown files.

To disable this:

```bash
jira-sync push ./tickets --no-write-back
```

This may be useful in temporary or experimental workflows.

However, normal usage should retain write-back because `jira_key` is what makes subsequent synchronization idempotent.

Without write-back, pushing the same new ticket again may create another Jira issue.

---

# Recommended workflow

A typical human workflow is:

```bash
jira-sync validate ./tickets
jira-sync plan ./tickets
jira-sync push ./tickets
```

For an AI coding agent:

```text
1. Create or modify Markdown ticket files.

2. Run:
   jira-sync validate ./tickets

3. Fix any validation errors.

4. Run:
   jira-sync plan ./tickets

5. Present the plan to the human.

6. Wait for authorization to modify Jira.

7. Run:
   jira-sync push ./tickets --yes

8. Preserve the jira_key values written into the Markdown files.
```

The intended responsibility split is:

```text
AI agent
    │
    ├── interpret requirements
    ├── write ticket content
    ├── organize work
    └── propose changes
          │
          ▼
      jira-sync
          │
          ├── validate
          ├── transform
          ├── call Jira API
          ├── enforce issue identity
          └── persist Jira keys
```

---

# Example: creating an epic and stories

Assume the following files.

## `tickets/agent-platform.md`

```markdown
---
id: agent-platform
type: Epic
labels:
  - agents
---

# Agent platform

Create the foundational platform for running internal AI agents.

## Goals

- Standardize execution
- Add observability
- Support reusable tools
```

## `tickets/observability.md`

```markdown
---
id: agent-observability
type: Story
parent: agent-platform
labels:
  - observability
---

# Add agent observability

Add tracing and execution metrics.

## Acceptance Criteria

- Agent runs produce traces
- Tool calls are represented as spans
- Token usage is recorded
```

## `tickets/evals.md`

```markdown
---
id: agent-evals
type: Story
parent: agent-platform
labels:
  - evals
---

# Add automated agent evaluations

Create an evaluation pipeline for representative agent tasks.
```

Run:

```bash
jira-sync validate ./tickets
```

then:

```bash
jira-sync plan ./tickets
```

The plan will identify all three issues as creates.

When:

```bash
jira-sync push ./tickets
```

is executed, `jira-sync` creates the epic first.

Suppose Jira returns:

```text
ENG-101
```

The parent file becomes:

```yaml
---
id: agent-platform
type: Epic
labels:
- agents
jira_key: ENG-101
---
```

The child stories can then be created using `ENG-101` as their parent.

Their returned Jira keys are also persisted locally.

---

# Updating existing issues

Suppose a ticket now contains:

```yaml
---
id: agent-observability
jira_key: ENG-102
type: Story
parent: agent-platform
---
```

If you modify its Markdown description and run:

```bash
jira-sync plan ./tickets
```

the ticket is reported as:

```text
UPDATE
```

Running:

```bash
jira-sync push ./tickets
```

sends the current local fields and description to:

```text
ENG-102
```

rather than creating a new issue.

---

# Source-of-truth model

Version 0.1 is primarily a:

```text
Markdown → Jira
```

synchronization tool.

Local Markdown represents the desired values being pushed to Jira.

It is not currently a bidirectional synchronization system.

Changes made directly in Jira are not pulled back into the Markdown files.

This distinction is important when deciding how tickets should be maintained.

If Markdown is being treated as the canonical authoring format, it is generally best to make substantive edits locally and then push them to Jira.

---

# Idempotency

`jira-sync` uses `jira_key` as issue identity.

Without a Jira key:

```yaml
id: observability
```

the ticket is considered new.

With a Jira key:

```yaml
id: observability
jira_key: ENG-102
```

the ticket represents the existing Jira issue `ENG-102`.

This means the normal lifecycle is:

```text
local Markdown
     ↓
CREATE
     ↓
Jira returns ENG-102
     ↓
jira_key written locally
     ↓
future pushes are UPDATEs
```

The local `id` is useful for relationships.

The Jira key is the authoritative identity of the external Jira issue.

---

# Parent dependency ordering

New issues may reference other new issues using local IDs.

For example:

```text
Epic A
  ↓
Story B
  ↓
Task C
```

If the files contain:

```yaml
# Epic
id: epic-a
```

```yaml
# Story
id: story-b
parent: epic-a
```

```yaml
# Task
id: task-c
parent: story-b
```

`jira-sync` delays child creation until the required parent has been assigned a Jira key.

The resulting creation order is:

```text
Epic A
  → Jira key ENG-100

Story B
  → parent ENG-100
  → Jira key ENG-101

Task C
  → parent ENG-101
  → Jira key ENG-102
```

Circular relationships cannot be resolved and result in an error.

---

# Error handling

`jira-sync` exits with a non-zero status when validation, planning, Jira communication, or dependency resolution fails.

Jira API errors are surfaced with the HTTP status code and available Jira error information.

For example:

```text
Jira API 400: ...
```

Possible causes include:

- invalid issue type
- invalid project
- missing required Jira fields
- invalid custom-field values
- insufficient Jira permissions
- invalid parent relationships
- authentication failure

Because Jira projects can have different schemas, not every invalid field combination can be detected locally.

Using `plan` before `push` is strongly recommended.

---

# Agent integration

`jira-sync` is intentionally agent-agnostic.

Claude Code, Codex, Hermes, or another agent can call the same executable:

```bash
jira-sync validate
jira-sync plan
jira-sync push
```

Agent-specific files should describe how to invoke `jira-sync`, rather than contain their own Jira implementation.

For example:

```text
Claude skill ──────┐
Codex instructions ├──── jira-sync ──── Jira REST API
Hermes tool ───────┘
```

This ensures that:

- Jira behavior is implemented once
- synchronization semantics are consistent
- API handling can be independently tested
- agents remain replaceable
- credentials do not need to be embedded in prompts

---

# Current limitations

Version 0.1 is deliberately conservative.

## Jira Cloud only

The implementation targets Jira Cloud REST API v3.

Jira Server and Jira Data Center have not been implemented.

---

## No Jira-to-Markdown synchronization

There is currently no:

```bash
jira-sync pull
```

or bidirectional reconciliation.

Changes made directly in Jira are not automatically reflected locally.

---

## No semantic `NOOP` detection

Although the internal action model includes `NOOP`, v0.1 does not fetch and compare all Jira field values.

A file with a valid `jira_key` is therefore planned as:

```text
UPDATE
```

even if the local representation has not changed.

A future version may compare local and remote representations before deciding whether an update is required.

---

## No deletion

Deleting a Markdown file does not delete the corresponding Jira issue.

There is intentionally no automatic issue-deletion behavior in v0.1.

---

## No field-schema discovery

Jira projects often contain custom:

- issue types
- workflows
- fields
- priorities
- required fields

`jira-sync` does not yet query Jira metadata to infer these schemas.

Project-specific fields must currently be supplied explicitly.

---

## No bulk writes

Each issue is created or updated using an individual Jira REST request.

This makes:

- parent resolution straightforward
- failure behavior easier to understand
- partial execution easier to diagnose

Bulk operations may be added later where appropriate.

---

## Authentication is currently API-token based

OAuth is not currently implemented.

Version 0.1 is primarily intended for personal and internal automation where an Atlassian API token is appropriate.

---

# Safety considerations

`validate` is local-only and does not modify Jira.

`plan` does not modify Jira.

`push` does modify Jira.

A recommended permission policy for autonomous agents is therefore:

```text
validate    freely allowed
plan        freely allowed
push        human approval required
push --yes  allowed only after explicit approval
```

This maintains a useful human-in-the-loop boundary around externally visible changes.

---

# Development

Run the tests from the `agent-tools` repository:

```bash
pytest
```

The Jira client is isolated from ticket parsing and planning logic so core behavior can be tested without accessing a live Jira instance.

The main implementation modules are:

```text
src/agent_tools/jira_sync/
├── adf.py
├── cli.py
├── config.py
├── jira.py
├── markdown.py
├── models.py
├── planner.py
└── sync.py
```

Their responsibilities are approximately:

```text
cli.py
    command-line interface

config.py
    environment and .ai-tools.toml configuration

markdown.py
    ticket discovery, parsing, and Jira-key write-back

models.py
    internal ticket and planning models

adf.py
    Markdown → Atlassian Document Format conversion

planner.py
    validation and CREATE/UPDATE planning

sync.py
    dependency ordering and synchronization execution

jira.py
    Jira Cloud REST API client
```

---

# Future directions

Potential enhancements include:

- semantic diffing and `NOOP` actions
- Jira field/schema discovery
- OAuth authentication
- Jira → Markdown pull
- conflict detection
- richer Markdown/ADF support
- attachments
- issue links and dependencies beyond parent relationships
- comments
- transitions and workflow operations
- bulk operations
- machine-readable plan output such as JSON
- structured agent-facing output
- MCP wrappers around the same underlying Python implementation

The CLI should remain useful independently of any particular AI agent or MCP implementation.
