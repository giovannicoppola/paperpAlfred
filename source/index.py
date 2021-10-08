#!/usr/bin/env python
# encoding: utf-8
#
# Copyright (c) 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-07-03
#
# edited on Saturday, November 14, 2020 for the paperpile/alfred code
# @giovannicoppoIa


from __future__ import print_function, unicode_literals

import sys
import os
import sqlite3
import csv
from time import time


from workflow import Workflow

from config import INDEX_DB, DATA_FILE

log = None




def create_index_db():
    
    log.info('Creating index database')
    con = sqlite3.connect(INDEX_DB)
    with con:
        cur = con.cursor()
        cur.execute(
            "CREATE VIRTUAL TABLE papers USING fts3(_id,abstract, citekey, fileName, first, folder,folderID, fullReference, gdrive_id, journal, label, labelID,last, pdfFlag, pmid, subtitle, title, type, year)") 
            #FTS3 and FTS4 are SQLite virtual table modules that allows users to perform full-text searches on a set of documents.


def update_index_db():
    """Read in the data source and add it to the search index database"""
    start = time()
    log.info('Updating index database')
    con = sqlite3.connect(INDEX_DB)
    count = 0
    with con:
        cur = con.cursor()
        with open(DATA_FILE, 'rb') as fp:
            next (fp)
            reader = csv.reader(fp, delimiter=b',')
            for row in reader:
                #log.info (row)
                _id,abstract, citekey, fileName, first, folder,folderID, fullReference, gdrive_id, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, type, year = [v.decode('utf-8') for v in row]
                #id_ = int(id_)
                cur.execute("""INSERT OR IGNORE INTO
                            papers (_id,abstract, citekey, fileName, first,folder,folderID, fullReference, gdrive_id, journal, label,labelID, last,pdfFlag, pmid, subtitle, title, type, year)
                            VALUES (?,?, ?, ?, ?, ?, ?, ?,?,?, ?, ?, ?, ?,?,?,?,?,?)
                            """, (_id,abstract, citekey, fileName, first,folder,folderID, fullReference, gdrive_id, journal, label,labelID, last,pdfFlag, pmid, subtitle, title, type, year))
                # log.info('Added {} by {} to database'.format(title, author))
                count += 1
    log.info('{} items added/updated in {:0.3} seconds'.format(
             count, time() - start))


def main(wf):
    if not os.path.exists(INDEX_DB):
        print ("Creating index")
        create_index_db()
    update_index_db()
    log.info('Index database update finished')


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
