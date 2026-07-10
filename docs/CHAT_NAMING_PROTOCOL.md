# Chat & Session Naming + Vault Archiving Protocol

A single standard for (1) naming Claude chats (Claude.ai) and Cowork / Claude
Code sessions, and (2) archiving them as summary notes in the Obsidian vault —
so history is sortable, groupable, searchable, and durable.

## The format

```
YYYY-MM-DD · AREA · Topic [· vN] [· ↻YYYY-MM-DD]
```

Example: `2026-07-01 · INV · Convolo Group · v2 · ↻2026-07-10`

| Segment       | Rule                                                                                    |
| ------------- | --------------------------------------------------------------------------------------- |
| `YYYY-MM-DD`  | ISO date the chat was **created**. 4-digit year, zero-padded month & day. Fixed forever. |
| ` · `         | Separator: **space + middle dot (·, U+00B7) + space**. Never a hyphen.                  |
| `AREA`        | An uppercase [area code](#area-codes). Exactly one.                                      |
| `Topic`       | Short, specific description. Sentence case. No trailing period.                          |
| `· vN`        | Optional. Version suffix for iterations of the **same** topic: `· v2`, `· v3`.          |
| `· ↻YYYY-MM-DD` | Optional. The **most recent interaction** date. Omitted while it equals the created date; appears once the chat is revisited on a later day. |

### Rules

1. **Created date is fixed.** It never changes. The `↻` date carries "last touched".
2. **`↻` last-active date** advances every time you return to the chat. In Cowork
   it's updated automatically on resume; on Claude.ai you bump it by hand when you
   rename, or (more reliably) rely on the vault note's `last_active` frontmatter.
3. **One area only.** If a chat spans two areas, pick the primary one.
4. **Topic ≤ ~6 words**, leading with the proper noun (company, project, deliverable).
5. **No trailing punctuation** on the topic.
6. **Versions, not dates, track iterations.** `· v2` = second pass at the same thing.

### Common drift to avoid

Real mistakes seen in existing history — the format above prevents them:

| Wrong                                   | Why                              | Right                                 |
| --------------------------------------- | -------------------------------- | ------------------------------------- |
| `026-07-09 · INV · Deal review`         | Dropped leading `2` of the year  | `2026-07-09 · INV · Deal review`      |
| `2026-07-03 - INV - Kinly investment`   | Hyphens instead of middle dots   | `2026-07-03 · INV · Kinly investment` |
| `2026-06- 29 · INV · Convolo`           | Stray space in the date          | `2026-06-29 · INV · Convolo`          |
| `2026-07-08 · KW · W27 Post-Send QA.`   | Trailing period on topic         | `2026-07-08 · KW · W27 Post-Send QA`  |

## Area codes

> **Confirm these meanings.** The codes come from existing chat history; the
> descriptions are inferred. Correct any that are wrong and add missing ones —
> this table is the authority once agreed.

| Code   | Area (confirm)                        | Example topic                    |
| ------ | ------------------------------------- | -------------------------------- |
| `INV`  | Investing — deals, positions, reviews | `Convolo Group · v2`             |
| `LTX`  | Legal / tax / compliance              | `Convolo NDA review`             |
| `FOO`  | Family office operations              | `Falcon Green comp/dividend`     |
| `KW`   | _(confirm — meaning unknown)_         | `W27 Post-Send QA`               |
| `SYS`  | Systems / infrastructure / meta-work  | `Anthropic advisor/orchestrator` |
| `PERS` | Personal                              | `Coffee Logger`                  |

Keep codes **short (2–4 letters), uppercase, stable**. Adding a code is deliberate.

## How naming is applied per surface

| Surface                               | Enforcement                                                                          |
| ------------------------------------- | ------------------------------------------------------------------------------------ |
| **Claude.ai chat** (web / mobile / desktop) | **Manual.** Auto-titles can't be templated. Rename each chat to this format (tap the title → Rename). |
| **Cowork / Claude Code sessions**     | **Automatic.** The `SessionStart` hook names sessions on start and updates the `↻` date on resume. |

### The automatic hook

`.claude/hooks/session-title.py` runs when a session starts/resumes in this repo:

- **Created date** — recorded per session on first start (persisted under
  `.claude/state/`, which is git-ignored) so it stays fixed across resumes.
- **AREA** — read from `.claude/chat-area` (currently `SYS`), or overridden per
  session with the `CLAUDE_CHAT_AREA` environment variable.
- **Topic** — derived from the git branch: the owner prefix (`claude/`) and any
  trailing random suffix are stripped, dashes become spaces. On `main`/`master`
  it falls back to the repo folder name.
- **↻ last-active date** — set to today; shown only once it differs from the
  created date.

Override any session title with `/rename`, or at launch with
`claude -n "2026-07-10 · INV · Some topic"`. Change the repo's default area by
editing `.claude/chat-area`.

## Archiving to the Obsidian vault

Chats worth keeping are saved as **summary notes** in the vault. The vault is
git-backed, so the reliable write path (from any surface, local or remote) is a
commit to the vault's git repo.

### Note format

One Markdown file per chat, named after the protocol (the `↻` date is *not* in
the filename, so the same note updates in place as `last_active` advances):

```
Chats/2026-07-01 · INV · Convolo Group · v2.md
```

```yaml
---
title: "2026-07-01 · INV · Convolo Group · v2 · ↻2026-07-10"
created: 2026-07-01
last_active: 2026-07-10
area: INV
topic: "Convolo Group"
version: 2
source: cowork          # or claude.ai
tags: [chat, INV, cowork]
---
```

Body sections: **Summary**, **Key points**, **Decisions**, **Follow-ups**, **Links**.
`created` and `last_active` are queryable in Obsidian (e.g. Dataview) for sorting
and "what did I touch this week" views.

### Generating a note

`bin/vault-note.py` formats a note from the metadata plus a summary you pipe in:

```bash
echo "$SUMMARY" | bin/vault-note.py \
    --area INV --topic "Convolo Group" \
    --created 2026-07-01 --last-active 2026-07-10 \
    --version 2 --source cowork \
    --out /path/to/Vault/Chats
```

Omit `--out` to print the note to stdout; omit the summary to get a fillable skeleton.

### Getting the note into the vault

Because the vault lives in its own git repo (not this one), saving is a
clone → write → commit → push into **that** repo. To wire this up, the vault repo
must be added to the session and the target folder confirmed (default `Chats/`).
For Claude.ai chats, ask Claude to "save this to the vault" and it will generate
the note and commit it to the vault repo.
