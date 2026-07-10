# Chat & Session Naming + Vault Archiving Protocol

A single standard for (1) naming Claude chats (Claude.ai) and Cowork / Claude
Code sessions, and (2) archiving them as summary notes in the Obsidian vault —
so history is sortable, groupable, searchable, and durable.

## The format

```
YYYY-MM-DD · AREA · Sub · Topic [· vN] [· ↻YYYY-MM-DD]
```

Examples:
- `2026-07-09 · INV · Deal · Convolo Group`
- `2026-07-01 · INV · Deal · Convolo Group · v2 · ↻2026-07-10`
- `2026-07-08 · KW · Bugfix · W27 post-send QA`

`Sub` is **optional** — drop it for quick or one-off chats and the format
collapses to `YYYY-MM-DD · AREA · Topic`.

| Segment        | Rule                                                                                    |
| -------------- | --------------------------------------------------------------------------------------- |
| `YYYY-MM-DD`   | ISO date the chat was **created**. 4-digit year, zero-padded. Fixed forever.            |
| ` · `          | Separator: **space + middle dot (·, U+00B7) + space**. Never a hyphen.                  |
| `AREA`         | An uppercase [area code](#area-codes). Exactly one.                                      |
| `Sub`          | Optional [sub-area](#sub-areas) token, Title case, from the area's list.                 |
| `Topic`        | Short, specific description. Sentence case. No trailing period.                          |
| `· vN`         | Optional. Version suffix for iterations of the **same** topic: `· v2`, `· v3`.          |
| `· ↻YYYY-MM-DD` | Optional. The **most recent interaction** date. Omitted while it equals the created date; appears once the chat is revisited on a later day. |

### Rules

1. **Created date is fixed.** It never changes. The `↻` date carries "last touched".
2. **`↻` last-active date** advances every time you return to the chat. In Cowork
   it's updated automatically on resume; on Claude.ai rely on the vault note's
   `last_active` frontmatter (or bump it by hand when you rename).
3. **One area, at most one sub.** If a chat spans two areas, pick the primary one.
4. **Sub comes from the area's list.** Keep sub-areas closed and consistent; if you
   need a new one, add it to the table below rather than coining ad-hoc tokens.
5. **Topic ≤ ~6 words**, leading with the proper noun (company, project, deliverable).
6. **No trailing punctuation** on the topic.
7. **Versions, not dates, track iterations.** `· v2` = second pass at the same thing.

### Common drift to avoid

| Wrong                                   | Why                              | Right                                 |
| --------------------------------------- | -------------------------------- | ------------------------------------- |
| `026-07-09 · INV · Deal review`         | Dropped leading `2` of the year  | `2026-07-09 · INV · Deal review`      |
| `2026-07-03 - INV - Kinly investment`   | Hyphens instead of middle dots   | `2026-07-03 · INV · Kinly investment` |
| `2026-06- 29 · INV · Convolo`           | Stray space in the date          | `2026-06-29 · INV · Convolo`          |
| `2026-07-08 · KW · W27 Post-Send QA.`   | Trailing period on topic         | `2026-07-08 · KW · W27 post-send QA`  |

## Area codes

Top-level areas are the coarse buckets shown in the title — keep them **few and
memorable**. Finer classification lives in the sub-area token and in the vault
note's `entity` / `tags` fields, not in more top-level codes.

| Code   | Area                                  | Example topic                    |
| ------ | ------------------------------------- | -------------------------------- |
| `INV`  | Investing — deals, positions, reviews | `Convolo Group · v2`             |
| `LTX`  | Legal / tax / compliance              | `Convolo NDA review`             |
| `FOO`  | Family office operations              | `Falcon Green comp/dividend`     |
| `KW`   | WNAP — Python development             | `W27 post-send QA`               |
| `SYS`  | Systems / infrastructure / meta-work  | `Anthropic advisor/orchestrator` |
| `PERS` | Personal                              | `Coffee Logger`                  |

Keep codes **short (2–4 letters), uppercase, stable**. Adding a code is deliberate.

## Sub-areas

Optional second token, one closed list per area. Title case. Extend a list here
rather than inventing tokens per chat.

| Area   | Sub-areas                                         |
| ------ | ------------------------------------------------- |
| `INV`  | Deal · Portfolio · Diligence · Review · Thesis    |
| `LTX`  | NDA · Tax · Structure · Compliance · Contract     |
| `FOO`  | Comp · Dividend · Gift · Admin · Banking          |
| `KW`   | Feature · Bugfix · Refactor · Infra · Release     |
| `SYS`  | Vault · Notebook · Docs · Agent · Config          |
| `PERS` | Health · Log · Travel · Misc                      |

For cross-area retrieval, the **entity** (company / project / person) is captured
separately in the vault note's `entity` field and tags — so "everything about
Convolo" spans the INV deal, the LTX NDA, and the FOO dividend without needing it
in the title code.

## How naming is applied per surface

| Surface                               | Enforcement                                                                          |
| ------------------------------------- | ------------------------------------------------------------------------------------ |
| **Claude.ai chat** (web / mobile / desktop) | **Manual.** Auto-titles can't be templated. Rename each chat to this format (tap the title → Rename). |
| **Cowork / Claude Code sessions**     | **Automatic.** The `SessionStart` hook names sessions on start and updates the `↻` date on resume. |

### The automatic hook

`.claude/hooks/session-title.py` runs when a session starts/resumes in this repo:

- **Created date** — recorded per session on first start (persisted under
  `.claude/state/`, git-ignored) so it stays fixed across resumes.
- **AREA** — from `.claude/chat-area` (currently `SYS`), or the `CLAUDE_CHAT_AREA`
  environment variable.
- **Sub** — from `.claude/chat-sub` or the `CLAUDE_CHAT_SUB` env var. Optional;
  omitted if unset.
- **Topic** — derived from the git branch: owner prefix (`claude/`) and any trailing
  random suffix stripped, dashes → spaces. On `main`/`master`, the repo folder name.
- **↻ last-active date** — today; shown only once it differs from the created date.

Override any session title with `/rename`, or at launch with
`claude -n "2026-07-10 · INV · Deal · Some topic"`. Change the repo defaults by
editing `.claude/chat-area` and `.claude/chat-sub`.

## Archiving to the Obsidian vault

Chats worth keeping are saved as **summary notes** in the vault. The vault is
git-backed, so the reliable write path (from any surface, local or remote) is a
commit to the vault's git repo.

### Note format

One Markdown file per chat, named after the protocol (the `↻` date is *not* in the
filename, so the same note updates in place as `last_active` advances):

```
Chats/2026-07-01 · INV · Deal · Convolo Group · v2.md
```

```yaml
---
title: "2026-07-01 · INV · Deal · Convolo Group · v2 · ↻2026-07-10"
created: 2026-07-01
last_active: 2026-07-10
area: INV
subarea: "Deal"
topic: "Convolo Group"
entity: "Convolo Group"
version: 2
source: cowork          # or claude.ai
tags: [chat, INV, deal, convolo-group, cowork]
---
```

Body sections: **Summary**, **Key points**, **Decisions**, **Follow-ups**, **Links**.
`created` / `last_active` / `entity` / `subarea` are all queryable in Obsidian
(e.g. Dataview) for sorting, cross-area entity views, and "what did I touch this week".

### Generating a note

`bin/vault-note.py` formats a note from the metadata plus a summary you pipe in:

```bash
echo "$SUMMARY" | bin/vault-note.py \
    --area INV --sub Deal --topic "Convolo Group" --entity "Convolo Group" \
    --created 2026-07-01 --last-active 2026-07-10 \
    --version 2 --source cowork \
    --out /path/to/Vault/Chats
```

Omit `--out` to print to stdout; omit `--sub`/`--entity` to leave them out; omit
the summary to get a fillable skeleton.

### Getting the note into the vault

Because the vault lives in its own git repo (not this one), saving is a
clone → write → commit → push into **that** repo. To wire this up, the vault repo
must be added to the session and the target folder confirmed (default `Chats/`).
For Claude.ai chats, ask Claude to "save this to the vault" and it will generate
the note and commit it to the vault repo.
