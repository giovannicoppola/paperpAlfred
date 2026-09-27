#!/usr/bin/env python3

import os


def _int_env(name, default):
    """Read an integer config value, falling back to `default` if the user
    cleared the field or typed something that is not a number."""
    try:
        return int(str(os.getenv(name, '')).strip())
    except ValueError:
        return default


MAXRES = _int_env('MAXRESULTS', 99)
LIBRARY_FILE = os.path.expanduser(os.getenv('PAPLIBRARY', ''))

WF_BUNDLE = os.getenv('alfred_workflow_bundleid', 'giovanni.paperpAlfred')
WF_FOLDER = os.path.expanduser('~') + "/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/" + WF_BUNDLE + "/"
INDEX_DB = WF_FOLDER + "index.db"
TIMESTAMP = WF_FOLDER + 'timestamp.txt'

if not os.path.exists(WF_FOLDER):
    os.makedirs(WF_FOLDER)
