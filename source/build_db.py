#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Rebuild the search index from a Paperpile JSON export.
#
# previously created on Sunday, February 28, 2021
# March 2022 updated to Python3, eliminated dependencies

import collections
import json
import os
import re
import sqlite3
import sys
import time

from config import INDEX_DB

# Fields kept from the export. Everything else is dropped before indexing.
SUBSET_FIELDS = {
    'title', 'published', 'abstract', 'issue', 'author', 'pages', 'citekey',
    'journal', 'volume', 'pmid', 'labelsNamed', 'foldersNamed', 'labels',
    'folders', 'attachments', 'subfolders', 'gdrive_id', '_id', 'pubtype',
    'kind',
}

# Dropped again once the flattened columns have been derived from them.
DERIVED_FROM = [
    'author', 'published', 'issue', 'pages', 'volume', 'labelsNamed',
    'foldersNamed', 'labels', 'folders', 'attachments', 'subfolders',
    'pubtype', 'kind',
]

# `kind` wins over `pubtype` for these, which are more useful to filter on.
KINDS = ['Commentary', 'Review', 'News']

# find(1) reads these as pattern syntax, so a title containing them would
# never match the file on disk. Bracket-escaping is what find expects.
GLOB_META = re.compile(r'([\[\]?])')


def log(s, *args):
    if args:
        s = s % args
    print(s, file=sys.stderr)


def JSONtoDB(myJSON, myTable, db, columns=None):
    """Write a list of flat dicts to an FTS5 table, replacing any existing one.

    FTS5 (rather than FTS3) gives us diacritic folding, so searching "Muller"
    finds "Müller" -- which FTS3's default tokenizer could not do.
    """
    column_list = list(columns) if columns else []
    for data in myJSON:
        for col in data.keys():
            if col not in column_list:
                column_list.append(col)

    if not column_list:
        # Nothing to index (e.g. a library with no folders at all). Create the
        # table anyway so queries against it return empty instead of throwing.
        column_list = ['placeholder']

    quoted = ', '.join('"{}"'.format(c.replace('"', '""')) for c in column_list)
    placeholders = ', '.join('?' * len(column_list))

    db.execute('DROP TABLE IF EXISTS "{}"'.format(myTable))
    db.execute(
        'CREATE VIRTUAL TABLE "{}" USING fts5({}, '
        'tokenize="unicode61 remove_diacritics 2")'.format(myTable, quoted))
    db.executemany(
        'INSERT INTO "{}" ({}) VALUES ({})'.format(myTable, quoted, placeholders),
        [[str(data.get(col, '')) for col in column_list] for data in myJSON])


def _joined(values):
    """Join names for the searchable text column."""
    return ','.join(str(v) for v in values)


def _pairs(names, ids):
    """Pair each label/folder name with its ID.

    Names and IDs used to be joined into strings and split apart again, which
    broke on any name containing a comma (it became two labels, each carrying
    the wrong ID) and raised IndexError whenever the two arrays disagreed in
    length. Pairing them up front avoids both.
    """
    return list(zip(names or [], ids or []))


def _summarise(groups, id_key, name_key, total_key, summary_key):
    """Turn the grouped counts into the rows Alfred lists."""
    rows = []
    for name, group in groups.items():
        parts = []
        for type_name, count in sorted(group['types'].items(),
                                       key=lambda kv: kv[1], reverse=True):
            if count:
                parts.append('{} ({}) '.format(_pretty_type(type_name), count))
        rows.append({
            name_key: name,
            total_key: str(group['total']),
            id_key: group['id'],
            summary_key: ''.join(parts),
        })
    return rows


def _pretty_type(type_name):
    return type_name.replace('PP_', '').replace('_', ' ').capitalize()


def _group_by(mySubset, pair_key):
    """Count publication types per label (or per folder).

    Type counts live in their own dict, so a publication type that happens to
    be named "Total" or "labelID" can no longer collide with the row's own
    bookkeeping keys.
    """
    groups = collections.OrderedDict()
    for item in mySubset:
        item_type = item.get('type')
        for name, group_id in item[pair_key]:
            if not name:
                continue
            group = groups.setdefault(
                name, {'id': group_id, 'types': collections.Counter(), 'total': 0})
            group['total'] += 1
            if item_type:
                group['types'][item_type] += 1
    return groups


PAPER_COLUMNS = [
    '_id', 'abstract', 'citekey', 'fileName', 'first', 'folder', 'folderID',
    'fullReference', 'journal', 'label', 'labelID', 'last', 'pdfFlag', 'pmid',
    'subtitle', 'title', 'gdrive_id', 'type', 'year',
]


def createLibrary(myLibrary, database=None):
    """Rebuild the whole index from the export at `myLibrary`.

    The index is built into a temporary file and moved into place only once
    every table is written, so a rebuild that is interrupted -- which Alfred
    does routinely, since the Script Filter terminates the previous script on
    each keystroke -- leaves the previous working index untouched.
    """
    target = database or INDEX_DB
    # Unique per process: Alfred can have two rebuilds in flight at once, and
    # a shared temp path would let one move the other's half-written file into
    # place. Stale temps from killed rebuilds are swept up first.
    tmp = '{}.{}.tmp'.format(target, os.getpid())
    _sweep_temps(target)

    with open(myLibrary, "r") as read_file:
        mydata = json.load(read_file)

    mySubset = []
    for item in mydata:
        if item.get('incomplete') == 1:      # skipping incomplete items
            continue
        mySubset.append({k: item[k] for k in SUBSET_FIELDS if k in item})

    for item in mySubset:
        _flatten(item)

    labels = _group_by(mySubset, 'labelPairs')
    folders = _group_by(mySubset, 'folderPairs')

    type_counts = collections.Counter(
        _pretty_type(item['type']) for item in mySubset if item.get('type'))

    for item in mySubset:
        del item['labelPairs'], item['folderPairs']

    papers = [{k: v for k, v in item.items() if k not in DERIVED_FROM}
              for item in mySubset]

    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    try:
        JSONtoDB(_summarise(labels, 'LabelID', 'label', 'totalLabel', 'summaryLabel'),
                 'Labels', db, columns=['label', 'totalLabel', 'LabelID', 'summaryLabel'])
        JSONtoDB(_summarise(folders, 'FolderID', 'folder', 'totalFolder', 'summaryFolder'),
                 'Folders', db, columns=['folder', 'totalFolder', 'FolderID', 'summaryFolder'])
        JSONtoDB([{'type': name, 'totalType': str(count)}
                  for name, count in type_counts.items()],
                 'Types', db, columns=['type', 'totalType'])
        JSONtoDB(papers, 'papers', db, columns=PAPER_COLUMNS)
        db.commit()
    finally:
        db.close()

    try:
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# A rebuild that has not touched its temp file for this long is dead, not slow.
STALE_TEMP_SECONDS = 3600


def _sweep_temps(target):
    """Delete temp indexes left behind by rebuilds that were killed.

    Only files that have gone stale are removed -- a temp belonging to a
    rebuild still running in a sibling process must be left alone.
    """
    folder = os.path.dirname(target) or '.'
    prefix = os.path.basename(target) + '.'
    cutoff = time.time() - STALE_TEMP_SECONDS
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if not (name.startswith(prefix) and name.endswith('.tmp')):
            continue
        path = os.path.join(folder, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def _flatten(item):
    """Derive the flat, searchable columns for a single record."""
    # Defaults first, so a record missing any of these cannot crash the build
    # or silently inherit a value from the record before it.
    item.setdefault('title', '')
    item.setdefault('pmid', '-')
    item.setdefault('citekey', '-')
    item.setdefault('journal', '-')
    item.setdefault('abstract', '')
    item.setdefault('author', [])
    item.setdefault('issue', '')
    item.setdefault('volume', '')
    item.setdefault('pages', '')
    item.setdefault('gdrive_id', '')
    item.setdefault('_id', '')
    item.setdefault('published', {})
    item.setdefault('attachments', [])
    item.setdefault('labels', [])
    item.setdefault('labelsNamed', [])
    item.setdefault('folders', [])
    item.setdefault('foldersNamed', [])
    item['fileName'] = ''
    item['pdfFlag'] = ' '

    item['journal'] = re.sub(r'\.', '', str(item['journal']))

    authors = [a for a in item['author'] if isinstance(a, dict)]
    authorBlock = ', '.join(a['formatted'] for a in authors if a.get('formatted'))
    firstAuthorLN = authors[0].get('last', '') if authors else ''
    lastAuthorLN = authors[-1].get('last', '') if authors else ''

    published = item['published'] if isinstance(item['published'], dict) else {}
    pubYear = str(published.get('year') or '-')

    item['first'] = firstAuthorLN
    item['last'] = lastAuthorLN
    item['year'] = pubYear

    myType = item.get('pubtype', '')
    if item.get('kind') in KINDS:
        myType = item['kind']
    item['type'] = myType

    item['labelPairs'] = _pairs(item['labelsNamed'], item['labels'])
    item['folderPairs'] = _pairs(item['foldersNamed'], item['folders'])
    item['label'] = _joined(item['labelsNamed'])
    item['labelID'] = _joined(item['labels'])
    item['folder'] = _joined(item['foldersNamed'])
    item['folderID'] = _joined(item['folders'])

    _attach_pdf(item, firstAuthorLN)

    # Show a single author once rather than as "Dolgin-Dolgin".
    byline = firstAuthorLN if firstAuthorLN == lastAuthorLN else \
        '{}-{}'.format(firstAuthorLN, lastAuthorLN)
    item['subtitle'] = '{}, {} {}'.format(byline, item['journal'], pubYear)

    item['fullReference'] = _full_reference(item, authorBlock, pubYear)


def _attach_pdf(item, firstAuthorLN):
    """Record how to find the PDF, preferring the article PDF over supplements."""
    attachments = [a for a in item['attachments'] if isinstance(a, dict)]
    if not attachments:
        return

    attachment = next((a for a in attachments if a.get('article_pdf') == 1),
                      attachments[0])

    if attachment.get('source_filename') == "[article_pdf].pdf":
        myFilename = attachment.get('filename', '')
    else:
        # A find(1) glob: first author plus the start of the title. Brackets
        # and question marks are escaped, or find would read them as pattern
        # syntax and never match titles like "[Corrigendum] ...".
        myTitle = GLOB_META.sub(r'[\1]', str(item['title'])[0:30])
        myFilename = GLOB_META.sub(r'[\1]', firstAuthorLN) + '*' + myTitle + '*'
        myFilename = myFilename.replace("...  ", "... ")

    item['fileName'] = myFilename
    item['pdfFlag'] = '📜'
    if attachment.get('gdrive_id'):
        item['gdrive_id'] = attachment['gdrive_id']


def _full_reference(item, authorBlock, pubYear):
    """Journal Year;Volume(Issue):Pages. PMID: nnn -- the volume is the number
    that belongs before the parenthesised issue; it used to be omitted and the
    issue printed in its place."""
    volume = str(item['volume'] or '')
    issue = str(item['issue'] or '')
    locus = volume
    if issue:
        locus = '{}({})'.format(volume, issue) if volume else '({})'.format(issue)
    pages = str(item['pages'] or '')
    if pages:
        locus = '{}:{}'.format(locus, pages) if locus else pages

    ref = '{}. {}. {} {}'.format(authorBlock, item['title'], item['journal'], pubYear)
    if locus:
        ref += ';' + locus
    return ref + '. PMID: ' + str(item['pmid'])
