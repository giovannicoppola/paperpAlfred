#!/usr/bin/python3 
# -*- coding: utf-8 -*-
# giovanni, March 2021, from @deanishe's template
# Modified from books, to show paper types for filtering
# Tuesday, March 15, 2022, 2:52 PM update to Python3


import sys
import sqlite3
from config import INDEX_DB
import json


myQuery=sys.argv[1]



db = sqlite3.connect(INDEX_DB)
cursor = db.cursor()
result = {"items": []}

if (not myQuery):
    cursor.execute("""SELECT * FROM Types ORDER BY CAST (totalType as integer) DESC""")
    resultsQ = cursor.fetchall()

else:    
    try:
        cursor.execute("""SELECT * FROM Types WHERE type MATCH ? ORDER BY CAST (totalType as integer) DESC""",(myQuery+ '*',))
        resultsQ = cursor.fetchall()
        
    except sqlite3.OperationalError as err:
        # If the query is invalid, show an appropriate warning and exit
        result= {"items": [{
        "title": "Error: " + str(err),
        "subtitle": "Invalid Query",
        "arg": ";;",
        "icon": {
                "path": "icons/Warning.png"
            }
        }]}
        print (json.dumps(result))
        raise err
        
    
if (resultsQ):
    for xx in resultsQ:

        result["items"].append({

        "title": xx[0] + " (" + xx[1]+")" ,     
        
        
        "valid": True,
        "icon": {
            "path": "icons/icon_type.png"
            },
        "variables": {
            "mySource": 'type',
            "myTypeID": xx[0],
        }
            })

    print (json.dumps(result))



if (myQuery and not resultsQ):
    result["items"].append({
    "title": "No matches",
    "subtitle": "Try a different query",
    
    "arg": "",
    "icon": {

            "path": "icons/Warning.png"
        }
    })
    
    print (json.dumps(result))
            


    

    