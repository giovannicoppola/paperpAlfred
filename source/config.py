#!/usr/bin/env python3

import os


MAXRES = os.path.expanduser(os.getenv('MAXRESULTS', ''))
LIBRARY_FILE = os.path.expanduser(os.getenv('PAPLIBRARY'))

BIBTEX_FILE = os.path.expanduser(os.getenv('PAPLIBRARY_BIB'))

WF_BUNDLE = os.getenv('alfred_workflow_bundleid')
WF_FOLDER = os.path.expanduser('~')+"/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/"+WF_BUNDLE+"/"
INDEX_DB = WF_FOLDER+"index.db"
TIMESTAMP = WF_FOLDER+'timestamp.txt'
TIMESTAMP_BIBTEX = WF_FOLDER+'timestamp_bibTeX.txt'

if not os.path.exists(WF_FOLDER):
     os.makedirs(WF_FOLDER)

