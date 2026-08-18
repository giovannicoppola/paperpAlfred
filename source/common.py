#!/usr/bin/env python3

# Shared helpers for the paperpAlfred script filters:
#   log()               debugging output to Alfred's log
#   emit() / fail()     Script Filter JSON output
#   ensure_index()      rebuild the index if the library changed
#   build_match_query() turn a user query into a safe FTS5 MATCH expression

import json
import os
import re
import sqlite3
import sys

from config import INDEX_DB, LIBRARY_FILE, TIMESTAMP


def log(s, *args):
    if args:
        s = s % args
    print(s, file=sys.stderr)


def emit(items):
    """Print a Script Filter response."""
    print(json.dumps({"items": items}))


def fail(title, subtitle=""):
    """Print a single warning item and exit cleanly.

    Exiting 0 matters: a non-zero exit makes Alfred show its own error sheet
    instead of the item we just built.
    """
    emit([{
        "title": title,
        "subtitle": subtitle,
        "valid": False,
        "icon": {"path": "icons/Warning.png"},
    }])
    sys.exit(0)


# ---------------------------------------------------------------- index

def ensure_index():
    """Make sure the index exists and is current, rebuilding it if not.

    Called by every entry point, so `ppl`/`ppf`/`ppty` work on a fresh
    install and stay in sync with the library.
    """
    if not LIBRARY_FILE:
        fail("Paperpile library not set",
             "Set the 'Paperpile Library' path in Configure Workflow")

    try:
        new_time = int(os.path.getmtime(LIBRARY_FILE))
    except OSError:
        fail("Library file missing!",
             "Cannot locate the Paperpile library file: {}".format(LIBRARY_FILE))

    if _index_is_current(new_time):
        return

    # Imported lazily so the search path does not pay for it on every keystroke.
    from build_db import createLibrary

    try:
        createLibrary(LIBRARY_FILE)
    except Exception as err:                                  # noqa: BLE001
        fail("Could not rebuild the index",
             "{}: {}".format(type(err).__name__, err))

    # Only now is the rebuild known to have succeeded. Writing the timestamp
    # earlier would mark a half-built (or killed) index as up to date, and
    # nothing would ever rebuild it.
    with open(TIMESTAMP, "w") as f:
        f.write(str(new_time))


def _index_is_current(new_time):
    """True only if a complete index exists and matches the library mtime."""
    if not os.path.exists(INDEX_DB) or not os.path.exists(TIMESTAMP):
        return False
    try:
        with open(TIMESTAMP) as f:
            old_time = int(f.readline())
    except (OSError, ValueError):
        return False
    if old_time != new_time:
        return False
    return _tables_present()


def _tables_present():
    """Guard against a truncated database left behind by a killed rebuild."""
    try:
        db = sqlite3.connect(INDEX_DB)
        try:
            found = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            db.close()
    except sqlite3.Error:
        return False
    return {'papers', 'Labels', 'Folders', 'Types'} <= found


# ---------------------------------------------------------------- queries

# Fields the user may prefix a term with, per the README.
SEARCH_FIELDS = {
    'title', 'abstract', 'citekey', 'first', 'last', 'journal',
    'folder', 'label', 'pmid', 'year', 'type', 'labelID', 'folderID',
}

_FIELD_RE = re.compile(r'^(\w+):(.*)$')


def _phrase(text):
    """Quote a term as an FTS5 string so punctuation can never be read as
    query syntax. Embedded double quotes are doubled, per SQL string rules."""
    return '"' + text.replace('"', '""') + '"'


def build_match_query(user_query, prefix_last=True):
    """Build an FTS5 MATCH expression from raw user input.

    Every term is quoted, so characters that are operators to FTS5 -- ( ) " *
    : ^ - and friends -- are searched for literally instead of raising
    "malformed MATCH expression" while the user is still typing.

    `field:value` is preserved as an FTS5 column filter. The final term gets a
    prefix `*` so results narrow as you type; a trailing space simply means
    there is no final term to prefix.
    """
    terms = []
    for token in user_query.split():
        field = None
        match = _FIELD_RE.match(token)
        if match and match.group(1) in SEARCH_FIELDS:
            field, token = match.group(1), match.group(2)
            if not token:
                continue          # a bare "label:" is still being typed
        terms.append((field, token))

    if not terms:
        return None

    parts = []
    for index, (field, token) in enumerate(terms):
        expr = _phrase(token)
        if prefix_last and index == len(terms) - 1:
            expr += '*'
        parts.append('{} : {}'.format(field, expr) if field else expr)
    return ' '.join(parts)


# ---------------------------------------------------------------- browsing

def browse(table, name_col, total_col, id_col, summary_col, icon, source_var, id_var):
    """Render the label / folder / type picker for one of the count tables.

    Columns are named explicitly rather than read positionally out of
    `SELECT *`, whose order depended on which keys the indexer happened to
    discover first.
    """
    ensure_index()
    myQuery = sys.argv[1] if len(sys.argv) > 1 else ''

    columns = [name_col, total_col, summary_col or name_col]
    if id_col:
        columns.append(id_col)
    select = 'SELECT {} FROM "{}"'.format(', '.join(columns), table)
    order = ' ORDER BY CAST({} AS INTEGER) DESC'.format(total_col)

    matchQuery = build_match_query(myQuery)
    db = sqlite3.connect(INDEX_DB)
    try:
        if matchQuery:
            rows = db.execute(
                '{} WHERE "{}" MATCH ?{}'.format(select, table, order),
                (matchQuery,)).fetchall()
        else:
            rows = db.execute(select + order).fetchall()
    except sqlite3.OperationalError as err:
        fail("Error: " + str(err), "Invalid Query")
    finally:
        db.close()

    if not rows:
        fail("No matches", "Try a different query")

    items = []
    for row in rows:
        name, total, summary = row[0], row[1], row[2]
        items.append({
            "title": "{} ({})".format(name, total),
            "subtitle": summary if summary_col else "",
            "valid": True,
            "icon": {"path": icon},
            "variables": {
                "mySource": source_var,
                id_var: row[3] if id_col else name,
            },
        })
    emit(items)
