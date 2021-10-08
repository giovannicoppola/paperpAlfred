#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-07-03
# Modified from books, to show folders for filtering

"""Workflow Script Filter to show search results in Alfred."""

from __future__ import print_function, unicode_literals

import sys
import csv
import os
import struct
from time import time

from workflow import Workflow, ICON_INFO, ICON_WARNING
from workflow.background import run_in_background, is_running

from config import FOLDERS_OUT

log = None



def main(wf):
    ## Checking that the library file exists
    if not FOLDERS_OUT:
        wf.add_item('Folders file missing!', 'cannot locate the Paperpile library file', icon=ICON_WARNING)
        wf.send_feedback()
        return

    with open(FOLDERS_OUT, 'r') as fp:
        print(fp.read())


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
