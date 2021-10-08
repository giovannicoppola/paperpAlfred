#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-07-03
# Modified from books, to show paper types for filtering

"""Workflow Script Filter to show search results in Alfred."""

from __future__ import print_function, unicode_literals

import sys
import csv
import os
import struct
from time import time

from workflow import Workflow, ICON_INFO, ICON_WARNING
from workflow.background import run_in_background, is_running

from config import INDEX_DB, TYPES_OUT

log = None



def main(wf):
    # Workflow requires a query
  #  query = wf.args[0]
    
    ## Checking that the library file exists
    if not TYPES_OUT:
        wf.add_item('Types file missing!', 'cannot locate the Paperpile library file', icon=ICON_WARNING)
        wf.send_feedback()
        return

    mylabels=[]
    with open(TYPES_OUT, "r") as fp:
        reader = csv.reader(fp, delimiter=b'\t')
        for row in reader:
            mylabel, myCount = [v.decode('utf-8') for v in row]
            
            toShow = mylabel + " ("+myCount+")"
            wf.add_item(toShow, valid=True, arg=mylabel, icon='icon_type.png')
        wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
