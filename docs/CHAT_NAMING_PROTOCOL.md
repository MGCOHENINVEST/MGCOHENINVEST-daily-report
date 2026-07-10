# Chat & Session Naming Protocol

A single standard format for naming Claude chats (Claude.ai) and Cowork /
Claude Code sessions, so history is sortable, groupable, and searchable.

## The format

```
YYYY-MM-DD · AREA · Topic [· vN]
```

Example: `2026-07-09 · INV · Convolo Group · v2`

| Segment    | Rule                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------- |
| `YYYY-MM-DD` | ISO date the chat was **started**. Always a 4-digit year, zero-padded month & day.       |
| ` · `        | Separator: **space + middle dot (·, U+00B7) + space**. Never a hyphen.                    |
| `AREA`       | An uppercase [area code](#area-codes). Exactly one.                                        |
| `Topic`      | Short, specific description. Sentence case. No trailing period.                            |
| `· vN`       | Optional. Version suffix for iterations of the **same** topic: `· v2`, `· v3`.            |

### Rules

1. **Date is fixed at creation.** Do not re-date a chat when you return to it.
   Continue it, or start a new one and bump the version (`· v2`).
2. **One area only.** If a chat spans two areas, pick the primary one; split the
   work if it really is two threads.
3. **Topic ≤ ~6 words.** Lead with the proper noun (company, project, deliverable):
   `Falcon Green comp/dividend`, not `Reviewing the comp and dividend for Falcon Green`.
4. **No trailing punctuation** on the topic.
5. **Versions, not dates, track iterations.** `· v2` means "second pass at the
   same thing", regardless of how many days later.

### Common drift to avoid

These are real mistakes seen in existing history — the format above prevents them:

| Wrong                                   | Why                                    | Right                              |
| --------------------------------------- | -------------------------------------- | ---------------------------------- |
| `026-07-09 · INV · Deal review`         | Dropped leading `2` of the year        | `2026-07-09 · INV · Deal review`   |
| `2026-07-03 - INV - Kinly investment`   | Hyphens instead of middle dots         | `2026-07-03 · INV · Kinly investment` |
| `2026-06- 29 · INV · Convolo`           | Stray space in the date                | `2026-06-29 · INV · Convolo`       |
| `2026-07-08 · KW · W27 Post-Send QA.`   | Trailing period on topic               | `2026-07-08 · KW · W27 Post-Send QA` |

## Area codes

> **Confirm these meanings.** The codes are taken from existing chat history;
> the descriptions are inferred. Correct any that are wrong and add missing ones —
> this table is the authority once agreed.

| Code   | Area (confirm)                        | Example topic                          |
| ------ | ------------------------------------- | -------------------------------------- |
| `INV`  | Investing — deals, positions, reviews | `Convolo Group · v2`                   |
| `LTX`  | Legal / tax / compliance              | `Convolo NDA review`                   |
| `FOO`  | Family office operations              | `Falcon Green comp/dividend`           |
| `KW`   | _(confirm)_                           | `W27 Post-Send QA`                     |
| `SYS`  | Systems / infrastructure / meta-work  | `Anthropic advisor/orchestrator`       |
| `PERS` | Personal                              | `Coffee Logger`                        |

Keep codes **short (2–4 letters), uppercase, stable**. Adding a code is a
deliberate act — prefer reusing an existing one.

## How it's applied per surface

| Surface                              | Enforcement                                                                                   |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| **Claude.ai chat** (web / mobile / desktop) | **Manual.** Auto-titles can't be templated. Rename each chat to this format (tap the title → Rename). |
| **Cowork / Claude Code sessions**    | **Automatic.** The `SessionStart` hook in `.claude/` names sessions on start (see below).      |

### The automatic hook

`.claude/hooks/session-title.py` runs when a Cowork / Claude Code session starts
in this repo and sets the title to:

```
<today> · <AREA> · <topic from git branch>
```

- **Date** — today's date.
- **AREA** — read from `.claude/chat-area` (currently `SYS`), or override per
  session with the `CLAUDE_CHAT_AREA` environment variable.
- **Topic** — derived from the git branch: the owner prefix (`claude/`) and any
  trailing random suffix are stripped, and dashes become spaces. On `main`/`master`
  it falls back to the repo folder name.

You can always override a session title mid-session with `/rename`, or at launch
with `claude -n "2026-07-10 · INV · Some topic"`.

To change the default area for this repo, edit `.claude/chat-area`.
