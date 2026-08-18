# paperpAlfred — Code Review

> **Status:** findings 1–12, plus the hygiene and documentation items, were
> fixed in the follow-up commit on this branch and are covered by
> `source/tests/test_index.py` (31 tests). This document is kept as the record
> of what was wrong and why. Items still open: adding a `LICENSE` file (a call
> for the author to make), trimming the duplicated icon assets, and excluding
> `__pycache__` from the release bundle at packaging time.
>
> **Packaging note:** the workflow gained a new file, `source/common.py`. It
> must be included when exporting the `.alfredworkflow`, or the Script Filters
> will fail to import.

Reviewed at commit `1bde18b`, workflow version 2.3. Every finding below was
reproduced by running the actual code against `source/demo_library.json`
(and mutated copies of it), not inferred from reading.

Overall: the workflow does the right thing architecturally — flatten the
Paperpile JSON export once into an FTS index, then answer keystrokes from
SQLite. Search latency is genuinely good (~30 ms per keystroke; a 5 000-record
rebuild takes ~1.1 s). The weak points are almost all in **robustness**: the
rebuild path has no failure recovery, and roughly a dozen code paths assume
the JSON export is well-formed in ways it is not guaranteed to be.

---

## Critical

### 1. An interrupted rebuild bricks the workflow permanently

`papers.py` writes the new timestamp **before** it rebuilds:

```python
with open(TIMESTAMP, "w") as f:
    f.write(str(new_time))     # papers.py:60-62
createLibrary(LIBRARY_FILE)    # papers.py:64
```

The `ppp` Script Filter is configured with `queuemode = 1` ("Terminate
previous script"). So while the rebuild is running, **the next character the
user types kills it** — and the timestamp already says "up to date", so no
later run will ever retry.

Reproduced: killing the process 350 ms into a rebuild leaves

```
sqlite3.OperationalError: no such table: papers
```

on every subsequent invocation, forever. Recovery requires manually deleting
the workflow cache folder. This is very likely the mechanism behind any
"it just stopped working" reports.

**Fix:** build into a temp DB and atomically rename it into place, then write
the timestamp only after `createLibrary` returns:

```python
createLibrary(LIBRARY_FILE)          # writes INDEX_DB + ".tmp", os.replace()s it
with open(TIMESTAMP, "w") as f:
    f.write(str(new_time))
```

Also add `os.path.exists(INDEX_DB)` to the rebuild condition, so a missing or
truncated DB triggers a rebuild even when the timestamp matches. Consider
`queuemode = 2` ("queue next and wait") on the `ppp` filter as a second layer.

### 2. `pubYear` leaks between records — and crashes on the first one

`build_db.py:167-184`:

```python
if (len(item['author'])) == 0:
    if ('last' in item['author']):        # `'last' in []` is always False — dead code
        firstAuthorLN = item['author']['last']
if (len(item['author'])) > 0:
    ...
    if ('year' in item['published'] ...):
        pubYear = item['published']['year']
    else:
        pubYear = "-"
item.update({'year': pubYear})            # ← reached even when never assigned
```

`pubYear` is only ever assigned inside the `len(author) > 0` branch, but it is
a plain local that survives across loop iterations. For a record with no
authors:

- if it is **not** the first record, it silently inherits the **previous
  record's year**. Verified: a record with `published.year = 1999` was indexed
  as `2012`, poisoning the sort order, `year:` searches, and the copied citation.
- if it **is** the first record, the whole rebuild dies with
  `UnboundLocalError: cannot access local variable 'pubYear'` — and per finding
  #1, that failure is then permanent.

Authorless records are not exotic: books, datasets, patents, reports, web pages.

**Fix:** initialise `pubYear = "-"` with the other defaults at the top of the
loop body, and hoist the year extraction out of the author branch (the two are
unrelated). Delete the dead `len(...) == 0` block.

### 3. A library with no folders still crashes the rebuild

The `# Note it currently fails if none of the references are in folders`
comment at `build_db.py:10` is still accurate. Reproduced:

```
KeyError: 'folder'
```

Two independent causes:

- `item.setdefault('folder', ...)` is never called (only `'label'` is, at line
  144), so `item['folder']` at line 341 raises when no record has `foldersNamed`.
- Even past that, `JSONtoDB` cannot handle an empty list: `column_list` comes
  out empty and it emits `create VIRTUAL table Folders USING FTS3 ()` /
  `insert into Folders () values (?)` → `sqlite3.OperationalError: near ")"`.

**Fix:** add `item.setdefault('folder', '')` and `setdefault('folderID', '')`;
and give `JSONtoDB` an early return that creates a fixed empty schema when
`myJSON` is empty. The same latent crash applies to a library with no labels
and no types.

---

## High

### 4. Commas in a label or folder name create phantom entries with wrong IDs

`build_db.py` joins names into a comma-delimited string and then splits it back
apart, matching names to IDs **by position**:

```python
myLabels   = item['label'].split(",")
myLabelIDs = item['labelID'].split(",")
...
labelCounts['labelID'] = myLabelIDs[lcc]
```

A single label named `Alzheimer, early onset` produced:

| label | count | labelID |
|---|---|---|
| `Alzheimer` | 1 | `3279e1bb-…` ← **actually the ID of `interesting`** |
| ` early onset` | 1 | `20c36c28-…` ← wrong ID |

So the label list shows two invented labels, and `⌃↩` on either opens the wrong
label in Paperpile. Commas in labels/folders are entirely normal
("Aging, cognition"). The leading-space variant also breaks matching.

**Fix:** stop round-tripping through a delimited string. Iterate
`zip(item['labelsNamed'], item['labels'])` directly. Keep the joined string
only as the FTS-searchable column, and prefer a delimiter that cannot appear in
a name (or store a proper child table).

### 5. `labelsNamed` / `labels` length mismatch → `IndexError`

Same code path. `myLabelIDs[lcc]` assumes the two arrays are the same length.
They are in the demo export, but nothing enforces it (a shared label, a label
deleted between syncs). A mismatch throws mid-rebuild — which, per #1, is
permanent. `zip()` fixes this along with #4.

### 6. `ppl` / `ppf` / `ppty` crash on a fresh install

Only `papers.py` builds the index. `labels.py`, `folders.py` and `myTypes.py`
just `sqlite3.connect(INDEX_DB)` — which happily creates an **empty** database
file — and query it. A new user whose first action is `ppl` (a documented,
hotkeyable entry point) gets:

```
sqlite3.OperationalError: no such table: Labels
```

Worse, the empty-query branch (`labels.py:22`) sits **outside** the `try`, so
even the error-item fallback doesn't fire.

**Fix:** factor the timestamp/rebuild check out of `papers.py` into a shared
`ensure_index()` and call it from all four entry points. That also fixes the
staleness problem: today, editing your library refreshes the papers index but
the label/folder/type lists stay stale until you happen to run `ppp`.

### 7. `raise err` defeats the error handler it belongs to

All four scripts print a friendly "Invalid Query" item and then immediately
`raise err`, so Alfred sees a non-zero exit and a traceback instead. This turns
ordinary typing into a visible error. Reproduced with characters a user types
constantly:

| typed | result |
|---|---|
| `gene"` | `malformed MATCH expression: [gene"*]` |
| `(paren` | `malformed MATCH expression: [(paren*]` |
| `"unclosed` | `malformed MATCH expression: ["unclosed*]` |

Titles containing parentheses and quotes are common, so this fires in normal use.

**Fix:** drop the `raise` and `sys.exit(0)` after printing the item. Better
still, sanitise the query before it reaches FTS — strip unbalanced quotes and
parentheses, and don't append `*` to a token that already ends in an operator
or is empty.

### 8. `MAXRESULTS` is string-interpolated into SQL

```python
LIMIT """ + MAXRES + """
```

`MAXRESULTS` is a user-editable config field with `required: False`. Clearing
it yields `LIMIT ` → `sqlite3.OperationalError: incomplete input` (reproduced,
both for unset and empty-string). It is also a straightforward SQL injection
point — low severity since it's the user's own config, but there's no reason to
leave it open.

**Fix:** `MAXRES = int(os.getenv('MAXRESULTS') or 99)` in `config.py`, wrapped
so a non-numeric value falls back to the default, and pass it as a bound
parameter (`LIMIT ?`).

### 9. `PAPLIBRARY` unset crashes before the friendly message can print

```python
LIBRARY_FILE = os.path.expanduser(os.getenv('PAPLIBRARY'))   # config.py:7
```

`os.getenv` returns `None` → `TypeError: expected str, bytes or os.PathLike
object, not NoneType`, raised at **import** time, so the carefully written
"Library file missing!" item in `papers.py:32-42` never gets a chance to run.
One-character fix: `os.getenv('PAPLIBRARY', '')`. (The same applies to
`expanduser(MAXRES)`, which is meaningless — a result count is not a path.)

### 10. The "full reference" prints the issue number where the volume belongs

```python
fullRef = ... + item['journal'] + ' ' + pubYear + ';' + item['issue'] + ':' + item['pages'] ...
```

`volume` is fetched into the subset (line 113) and then never used. Actual
output for the Bonasio 2010 record:

```
... Science 2010;5995:1068-1071. PMID: 20798317
```

`5995` is the *issue*; the volume is `329`. The correct form is
`Science 2010;329(5995):1068-1071`. Since "copy the complete reference"
(`⌃↩`) is one of the workflow's headline features, every citation it has ever
produced carries the wrong number.

**Fix:** `f"{journal} {year};{volume}({issue}):{pages}."`, omitting the
parenthesised issue when absent.

---

## Medium

### 11. Move from FTS3 to FTS5 — it fixes a documented "known issue"

The README lists as a known issue: *"special characters (e.g. ü) will need to
be entered in order to match the record."* That is purely an artifact of FTS3's
default `simple` tokenizer. Verified side by side:

```
FTS3 (simple),                    query "Muller*" → []
FTS5 (unicode61 remove_diacritics 2), query "Muller*" → [('Über die Müller Studie',)]
```

FTS5 also brings `bm25()` relevance ranking (currently results are ordered only
by year, so a title match and an incidental abstract match rank identically),
and better handling of the operator characters from #7. FTS3 has been the
legacy engine for over a decade.

### 12. PDF lookup by name breaks on bracket characters

`find "$PAPPATH" -name "$myFileName"` uses a glob pattern built from the title.
Titles containing `[` or `]` — `[Corrigendum]`, `[18F]-FDG PET`, chemical names
— are interpreted as glob character classes and silently fail to match:

```
pattern 'Jones*Effects of X [2020] on*'  → no match
pattern 'Jones*Effects of X ?2020? on*'  → matches
```

This is a concrete, fixable instance of the README's vague "there might be a
small number of cases where the PDF might not be retrievable". (Double quotes
in titles are *not* a problem — Alfred exports the variable into the
environment and `"$myFileName"` expands safely. I checked.)

Two smaller issues in the same action:

- With no match, `head -n 1 | tr \\n \\0 | xargs -0 open` still invokes `open`
  with **no arguments** (verified), which prints usage to stderr. Use
  `find ... -print -quit` and guard on an empty result with a user-visible
  "PDF not found" notification.
- `find` walks the entire Google Drive tree on every `↩`. Since
  `attachments[0].filename` and `gdrive_id` are already stored, prefer an exact
  path when `source_filename == "[article_pdf].pdf"` and keep the search as a
  fallback.

### 13. `year` is TEXT and sorted lexicographically

`ORDER BY year DESC` on a text column. It happens to work for 4-digit years and
places the `-` placeholder last, but any `2022-2023`, `in press`, or 3-digit
year misorders. `ORDER BY CAST(year AS INTEGER) DESC` is the cheap fix — note
`labels.py`/`folders.py` already do exactly this for their counts.

### 14. `SELECT *` with positional indexing

`labels.py:49-58` (and the folder/type equivalents) read `xx[0]`…`xx[3]`. Column
order is whatever key order `JSONtoDB` happened to discover from the first
record's dict. It works today only because the dict literal is written in that
order. Name the columns in the `SELECT`.

### 15. Separators are decided by value equality, not position

```python
if myAuthor['formatted'] == item['author'][-1]['formatted']:
    authorBlock += myAuthor['formatted']          # no comma — "this is the last one"
```

The same pattern appears for labels (line 200) and folders (line 218). It
detects "last element" by comparing *values*, so a repeated author name, or a
paper where a middle author's formatted name equals the last author's, silently
drops the separator. All three are just `', '.join(...)` / `','.join(...)`.

### 16. Only the first attachment is ever considered

`item['attachments'][0]` decides the filename, the 📜 flag and the `gdrive_id`.
A record whose first attachment is supplementary material (with the PDF second)
gets the wrong file. Scan for the entry with `article_pdf == 1` instead.

### 17. `item['labels']`, `item['folders']`, `item['attachments']`, `item['title']` are unguarded

These are read directly (lines 207, 225, 233, 239, 272) while their siblings get
`setdefault` treatment. `item['incomplete']` at line 119 has the same problem —
the guard that is supposed to filter incomplete records is itself the first
thing that throws on a record missing that key. Give them all defaults.

---

## Low / hygiene

- **`source/prefs.plist` is committed** even though `.gitignore` lists it
  (gitignore doesn't untrack existing files). It contains your personal paths
  including your Google account email:
  `~/Library/CloudStorage/GoogleDrive-giovannicoppola@gmail.com/…`.
  Run `git rm --cached source/prefs.plist`. It is not in the shipped `.alfredworkflow`, so this is repo hygiene, not a user-facing leak.
- **`__pycache__/*.pyc` ships in the release.** `paperpAlfred_2.3.alfredworkflow`
  contains `config.cpython-311.pyc`, `build_db.cpython-312.pyc`, etc. Stale
  bytecode can shadow the real source under a matching Python version. Exclude
  it from the build.
- **`paperpAlfred_functions.py` is dead code that is shipped anyway** and does
  `import bibtexparser` at module scope — a third-party package that is neither
  bundled nor present in macOS system Python. Nothing imports the module today,
  so it's harmless, but it contradicts the README's "removed dependencies" and
  is a trap for the next change. Delete it, or move it to a `sandbox/` folder
  excluded from releases. Its `JSONtoDB` and `log` are byte-for-byte duplicates
  of the ones in `build_db.py`.
- **`demo_db.py` executes at import time** with `myFile = 'path/to/library'`
  and no `if __name__ == "__main__":` guard. It ships in the release. Guard it
  or exclude it.
- **`from build_db import *`** in `papers.py` — wildcard imports pull in
  `json`, `sqlite3`, `re`, `sys`, `collections` and both helper functions.
  Import `createLibrary` explicitly.
- **`f.close` without parentheses**, three times (`papers.py:47, 55, 62`). They
  are no-ops that evaluate a bound method and discard it. Harmless inside
  `with`, but delete them.
- **Bare `except:`** at `papers.py:31` catches `KeyboardInterrupt` and
  `SystemExit` too. Use `except OSError:`.
- **SQLite connections are never closed** and `db.close()` is never called in
  any script; `JSONtoDB` opens a fresh connection per table (four per rebuild).
- **`--a` handling** (`papers.py:74-76`): the flag is detected with
  `"--a" in myQuery` but removed with `.replace(' --a', '')`, so a query of
  exactly `--a` flips the sort *and* leaves `--a` in the search terms. Match on
  a token boundary instead.
- **`type` shadows the builtin** in the result-unpacking tuple at `papers.py:156`.
- **`counters['Total']` / `counters['labelID']`** share a namespace with real
  publication-type names; a pubtype literally named "Total" would corrupt the
  counts. Use a nested dict.
- **~136 KB of JSON per keystroke.** Every one of the 99 results carries its
  full abstract in `variables`. It's fast enough today, but the abstract is only
  needed for the one item the user picks — worth fetching lazily by `_id` in the
  `⇧↩` action if you ever see lag on large libraries.
- **No `LICENSE` file**, though `papers.py`'s header declares MIT.
- **Duplicate icon assets.** `33BF8A0E-….png` and `icons/icon_folder.png` are
  byte-identical (md5 `0aae85fe…`, 308 KB each). The release is ~1.8 MB, almost
  entirely icons.
- **No tests and no CI.** A single fixture-based test that runs `createLibrary`
  over `demo_library.json` plus a handful of mutated copies (no authors, no
  folders, comma in a label, missing keys) would have caught findings #2–#6.

### Documentation drift

- README changelog stops at **2.1**; `info.plist` says **2.3**.
- README says `option-return (⌥⏎)` opens a label/folder in Paperpile. The
  workflow actually wires that to **`control-return (⌃⏎)`** (modifier `262144`).
- README says `ppty` supports `shift-return (⇧⏎)` to "open the folder in
  Paperpile". `ppty` has **no** modifier action wired at all, and "folder" looks
  like a copy-paste from the folder section.
- The known issue "label and folder search … will not be exact matches" is
  inherent to appending `*` to every query. If you switch to FTS5 you could
  offer an exact-match mode by quoting the term.

---

## Suggested order of work

1. Atomic rebuild + timestamp-after-success + rebuild-if-DB-missing (#1).
   Single highest-value change.
2. `pubYear` initialisation and the no-folders defaults (#2, #3) — both are
   total-failure modes.
3. Shared `ensure_index()` across all four entry points (#6, plus stale
   label/folder lists).
4. `zip()` the names to the IDs (#4, #5).
5. Remove `raise err`, bind `LIMIT` as a parameter, default the env vars
   (#7, #8, #9).
6. Fix the citation format (#10).
7. FTS3 → FTS5 (#11) — closes a documented known issue.
8. Escape glob metacharacters and prefer the exact stored filename (#12).
