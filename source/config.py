#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-07-03
#

"""Common settings."""

from __future__ import unicode_literals
import os
from workflow import Workflow, ICON_WARNING

wf = Workflow()

INDEX_DB = wf.cachefile('index.db')
DATA_FILE = wf.workflowfile('PAPERPILE_library.tsv')
LABELS_OUT = wf.workflowfile('LABELS_ALL.json')
FOLDERS_OUT = wf.workflowfile('FOLDERS_ALL.json')
TYPES_OUT = wf.workflowfile('TYPES_ALL.tsv')
MAXRES = os.path.expanduser(os.getenv('MAXRESULTS', ''))
LIBRARY_FILE = os.path.expanduser(os.getenv('PAPLIBRARY'))
TIMESTAMP = wf.workflowfile('timestamp.txt')
    

	
