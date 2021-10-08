#!/usr/bin/env python
# encoding: utf-8
#
# Search Paperpile library using Alfred
# Search engine structure and code from deanishe@deanishe.net  -- THANK YOU!
# MIT Licence. See http://opensource.org/licenses/MIT
#
# November 2020 - March 2021
#https://github.com/giovannicoppola/paperpAlfred/blob/main/README.md

"""Workflow Script Filter to show search results in Alfred."""

from __future__ import print_function, unicode_literals

import sys
import re
import os
import struct
import time



import sqlite3

from workflow import Workflow, ICON_INFO, ICON_WARNING
from workflow.background import run_in_background, is_running

from config import INDEX_DB, MAXRES, LIBRARY_FILE, TIMESTAMP
log = None







# Search ranking function
# Adapted from http://goo.gl/4QXj25 and http://goo.gl/fWg25i
def make_rank_func(weights):
    """`weights` is a list or tuple of the relative ranking per column.

    Use floats (1.0 not 1) for more accurate results. Use 0 to ignore a
    column.
    """
    def rank(matchinfo):
        # matchinfo is defined as returning 32-bit unsigned integers
        # in machine byte order
        # http://www.sqlite.org/fts3.html#matchinfo
        # and struct defaults to machine byte order
        bufsize = len(matchinfo)  # Length in bytes.
        matchinfo = [struct.unpack(b'I', matchinfo[i:i + 4])[0]
                     for i in range(0, bufsize, 4)]
        it = iter(matchinfo[2:])
        return sum(x[0] * w / x[1]
                   for x, w in zip(zip(it, it, it), weights)
                   if x[1])
    return rank


def main(wf):

    
    ## Checking that the library file exists
    if not LIBRARY_FILE:
        wf.add_item('Library file missing!', 'cannot locate the Paperpile library file', icon=ICON_WARNING)
        wf.send_feedback()
        return

    
## checking the timestamp
    with open(TIMESTAMP) as f:
        old_time = f.readline()
        f.close
    
    new_time = time.ctime(os.path.getmtime(LIBRARY_FILE))
    #log.info("old: "+old_time+" new: "+ new_time)
    ## time.ctime(os.path.getctime("test.txt"))) #time created

    if new_time != old_time:
        # notifying the user that the database is being rebuilt
        wf.add_item('Rebuilding database!', 'please try in a few seconds 👀', icon=ICON_INFO)
        wf.send_feedback()
        
        os.system('python rebuild.py')
        with open(TIMESTAMP, "w") as f:
            f.write(new_time)
            f.close

        

# getting the user query
    myQuery = wf.args[0]
    log.info ("my query is: " + myQuery)


    orderSel = "DESC"

    if "--a" in myQuery:
        orderSel = "ASC"
        myQuery = myQuery.replace (' --a','')

    #getting the source of the script
    mySource= sys.argv[2]

    
    #log.info ("My Source is: " + mySource)
    #log.info ("My Filter is: "+myFilter)
    if mySource == "label":
        myFilter= sys.argv[3].decode ('utf-8')
        #myFilter = re.escape (myFilter) ### this breaks the UTF8 encoding @#@
        myQuery = "labelID:"+myFilter+' '+myQuery
        #passing the label filter

    if mySource == "folder":
        myFilter= sys.argv[4].decode ('utf-8')
        myQuery = "folderID:"+myFilter+' '+myQuery
        #passing the folder filter

    if mySource == "type":
        myFilter= sys.argv[5].decode ('utf-8')
        myQuery = "type:"+myFilter+' '+myQuery
        #passing the folder filter

        
    index_exists = True

    # Create index if it doesn't exist
    if not os.path.exists(INDEX_DB):
        index_exists = False
        run_in_background('indexer', ['/usr/bin/python', 'index.py'])

    # Can't search without an index. Inform user and exit
    if not index_exists:
        wf.add_item('Updating search index…', 'Library file was outdated or changed',
                    icon=ICON_WARNING)
        wf.send_feedback()
        return

    # Inform user of update in case they're looking for something
    # recently added (and it isn't there)
    if is_running('indexer'):
        wf.add_item('Updating search index…',
                    'Fresher results will be available shortly',
                    icon=ICON_INFO)

    # Search!
    start = time.time()
    db = sqlite3.connect(INDEX_DB)
    # Set ranking function with weightings for each column.
    # `make_rank_function` must be called with a tuple/list of the same
    # length as the number of columns "selected" from the database.
    # In this case, `url` is set to 0 because we don't want to search on
    # that column
    db.create_function('rank', 1, make_rank_func((0, 1.0, 0, 0,0))) 
    cursor = db.cursor()

    
    try:
        cursor.execute("""SELECT _id,abstract, citekey, fileName, first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year FROM
                            (SELECT rank(matchinfo(papers))
                             AS r, _id, abstract, citekey, fileName,first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year
                             FROM papers WHERE papers MATCH ?)
                          ORDER BY year """ +orderSel + """ LIMIT """ + MAXRES + """ """, (myQuery + '*',))
        # search one column only: 'title:'+query + '*'
        results = cursor.fetchall()
    except sqlite3.OperationalError as err:
        # If the query is invalid, show an appropriate warning and exit
        if b'malformed MATCH' in err.message:
            wf.add_item('Invalid query', icon=ICON_WARNING)
            wf.send_feedback()
            return
        # Otherwise raise error for Workflow to catch and log
        else:
            raise err

    if (not myQuery):
        wf.add_item('Welcome to paperpAlfred 👋', 'Enter a query or ↩️ for help', icon="icon.png",valid=True,arg="ShowHelpWindow")
        


    if (myQuery and not results):
        wf.add_item('No matches', 'Try a different query', icon=ICON_WARNING)

    
    log.info('{} results for `{}` in {:0.3f} seconds'.format(
             len(results), myQuery, time.time() - start))

    # Output results to Alfred
    myResLen = str(len (results))
    countR=1
    for (_id, abstract, citekey, fileName, first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year) in results:
        aut_journ =  str(countR) + '/' + myResLen +  pdfFlag + subtitle + " 🏷" + label
        myArg = ";;".join([fileName,fullReference,subtitle+" "+pmid,abstract,citekey,gdrive_id,_id])
        wf.add_item(title, aut_journ, valid=True, arg=myArg, icon='icon.png')
        countR += 1

    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
