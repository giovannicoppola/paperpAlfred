#!/usr/bin/env python3

# Search Paperpile library using Alfred
# Search engine structure and code from deanishe@deanishe.net  -- THANK YOU!
# MIT Licence. See http://opensource.org/licenses/MIT
#
# November 2020 - March 2021
# https://github.com/giovannicoppola/paperpAlfred/blob/main/README.md
#
# February 2022, updated version for Python3

import os
import sqlite3
import sys

from common import build_match_query, emit, ensure_index, fail
from config import INDEX_DB, MAXRES

ensure_index()

myQuery = sys.argv[1] if len(sys.argv) > 1 else ''

orderSel = "DESC"
if "--a" in myQuery.split():
    orderSel = "ASC"
    myQuery = ' '.join(t for t in myQuery.split() if t != '--a')

# The label/folder/type pickers hand us the selected ID to scope the search.
mySource = os.getenv('mySource', '')
scope = {
    'label': ('labelID', os.getenv('myLabelID', '')),
    'folder': ('folderID', os.getenv('myFolderID', '')),
    'type': ('type', os.getenv('myTypeID', '')),
}.get(mySource)

matchQuery = build_match_query(myQuery)

if scope and scope[1]:
    scopeQuery = build_match_query('{}:{}'.format(*scope), prefix_last=False)
    matchQuery = '{} {}'.format(scopeQuery, matchQuery) if matchQuery else scopeQuery

if not matchQuery:
    emit([{
        "title": "Welcome to paperpAlfred 👋",
        "subtitle": "Enter a query or ↩️ for help",
        "valid": True,
        "arg": "ShowHelpWindow",
        "icon": {"path": "icons/paperpAlfred_ico.png"},
    }])
    sys.exit(0)

db = sqlite3.connect(INDEX_DB)
try:
    results = db.execute(
        """SELECT _id, abstract, citekey, fileName, first, folder, folderID,
                  fullReference, journal, label, labelID, last, pdfFlag, pmid,
                  subtitle, title, gdrive_id, type, year
             FROM papers
            WHERE papers MATCH ?
         ORDER BY CAST(year AS INTEGER) """ + orderSel + """, rank
            LIMIT ?""", (matchQuery, MAXRES)).fetchall()
except sqlite3.OperationalError as err:
    fail("Error: " + str(err), "Invalid Query")
finally:
    db.close()

if not results:
    fail("No matches", "Try a different query")

myResLen = str(len(results))
items = []
for countR, (_id, abstract, citekey, fileName, first, folder, folderID,
             fullReference, journal, label, labelID, last, pdfFlag, pmid,
             subtitle, title, gdrive_id, pubType, year) in enumerate(results, 1):
    items.append({
        "title": title,
        "subtitle": '{}/{}{}{} 🏷{}'.format(countR, myResLen, pdfFlag, subtitle, label),
        "variables": {
            "myFileName": fileName,
            "FullReference": fullReference,
            "shortPMID": subtitle + " " + pmid,
            "myAbstract": abstract,
            "myCitekey": citekey,
            "gdrive_id": gdrive_id,
            "paperpileID": _id,
        },
        "valid": True,
        "icon": {"path": "icons/paperpAlfred_ico.png"},
    })

emit(items)
