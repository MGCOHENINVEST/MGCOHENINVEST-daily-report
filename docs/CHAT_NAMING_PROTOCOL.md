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
8. **No leading prefixes or status tags** (e.g. `WIP`). The date must lead so titles
   sort chronologically. Track work-in-progress by **pinning** the chat, not in its name.

### Common drift to avoid

| Wrong                                   | Why                              | Right                                 |
| --------------------------------------- | -------------------------------- | ------------------------------------- |
| `026-07-09 · INV · Deal review`         | Dropped leading `2` of the year  | `2026-07-09 · INV · Deal review`      |
| `2026-07-03 - INV - Kinly investment`   | Hyphens instead of middle dots   | `2026-07-03 · INV · Kinly investment` |
| `2026-06- 29 · INV · Convolo`           | Stray space in the date          | `2026-06-29 · INV · Convolo`          |
| `2026-07-08 · KW · W27 Post-Send QA.`   | Trailing period on topic         | `2026-07-08 · KW · W27 post-send QA`  |
| `2026-07-08___OPS___Mac-File-Organisation` | Underscores instead of ` · `  | `2026-07-08 · OPS · Mac file organisation` |
| `2026-07-03 PERS Bookoo Shot-Capture PRD` | No separators at all          | `2026-07-03 · PERS · Bookoo Shot-Capture PRD` |
| `WIP 2026-07-07 · KW · Selection-contract` | Leading status prefix         | `2026-07-07 · KW · Selection-contract` |
| `2026-07-10 · Systems/Ops · …`          | Ad-hoc code variant              | `2026-07-10 · OPS · …`                |

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
| `OPS`  | Operations — file/machine/admin ops   | `Mac file organisation`          |
| `OBS`  | _(confirm label)_ — work capture / sweeps | `Uncaptured-work sweep — Convolo` |
| `PERS` | Personal                              | `Coffee Logger`                  |

Keep codes **short (2–4 letters), uppercase, stable**. Adding a code is deliberate.

Do **not** use ad-hoc variants — normalise to the code: `Systems/Ops` and `OPS`
both → `OPS`; spell an area out only in the `Topic`, never in the code slot.

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
| `OPS`  | Files · Backup · Migration · Machine · Admin      |
| `OBS`  | _(define once OBS label is confirmed)_            |
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
  `~/.claude/session-titles/`, user-level, so it stays fixed across resumes and
  the same hook works globally without writing into each repo).
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

### Use it in every repo (global install)

The hook above lives in this repo's `.claude/`. To name sessions in **all** your
repos, install it once at the user level:

```bash
bin/install-session-naming.py           # copies the hook to ~/.claude/hooks/
                                        # and adds the SessionStart hook to
                                        # ~/.claude/settings.json (backs up first)
bin/install-session-naming.py --print   # preview only, change nothing
bin/install-session-naming.py --uninstall
```

It's idempotent (won't duplicate the hook) and merges into existing settings
without disturbing other hooks. After installing, every repo names its sessions;
each repo can still set its own area via `.claude/chat-area` (or `CLAUDE_CHAT_AREA`),
defaulting to `SYS` where nothing is set.

## Archiving to the Obsidian vault

Chats worth keeping are saved as **summary notes** in the vault.

> **Security constraint — no remote.** The vault is a **local-only git repo with
> no remote**, by design: it holds sensitive notes and must never sit as plaintext
> on a hosted remote (GitHub etc.). Off-site persistence is handled by the vault's
> launchd auto-commit plus a daily **encrypted** bundle to OneDrive. Saving a note
> therefore means **writing a file into the local vault folder** — never a
> `git push`, clone, or `add_repo` to a hosted remote. Do not introduce one.

### Note format

One Markdown file per chat, named after the protocol (the `↻` date is *not* in the
filename, so the same note updates in place as `last_active` advances):

```
_chats/2026-07-01 · INV · Deal · Convolo Group · v2.md
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

### Saving a note (local write, no remote)

`bin/save-to-vault.sh` writes the note straight into the local vault `_chats/`
folder. It does **no git and no network** — the vault's own auto-commit and the
daily encrypted off-site bundle carry it away.

```bash
echo "$SUMMARY" | bin/save-to-vault.sh \
    --area INV --sub Deal --topic "Convolo Group" --entity "Convolo Group" \
    --created 2026-07-01 --last-active 2026-07-10 --version 2 --source cowork
```

Destination defaults to:

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/MC_Obsidian/_chats
```

Override it with the `VAULT_CHATS_DIR` environment variable. Omit `--sub`/`--entity`
to leave them out; omit the summary to write a fillable skeleton.

Under the hood it calls **`bin/vault-note.py`** (which formats the note and can also
print to stdout when run directly with `--out` omitted).

> This runs on the machine that holds the vault (your Mac). A remote Cowork session
> can't reach the local iCloud path, so for chats worth archiving, run the save
> where the vault lives — or generate the note text with `vault-note.py` and drop it
> into `_chats/` by hand.
