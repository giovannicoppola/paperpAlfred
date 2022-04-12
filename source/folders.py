#!/usr/bin/env python3
# v1.0 giovanni, March 2021, from @deanishe tutorial
# v2.0 Feb 2022 - Updated for Python3


import sys
import sqlite3
from config import INDEX_DB
import json


# getting the user query
myQuery=sys.argv[1]

result = {"items": []}


db = sqlite3.connect(INDEX_DB)
cursor = db.cursor()

if (not myQuery):
    cursor.execute("""SELECT * FROM Folders ORDER BY CAST (totalFolder as integer) DESC""")
    resultsQ = cursor.fetchall()

else:    
    try:
            
        cursor.execute("""SELECT * FROM Folders WHERE folder MATCH ? ORDER BY CAST (totalFolder as integer) DESC""",(myQuery+ '*',))
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
        "subtitle": xx[3],
        
        "valid": True,
        "icon": {
            "path": "icons/icon_folder.png"
            },
        "variables": {
            "mySource": 'folder',
            "myFolderID": xx[2],
        }
            })

    print (json.dumps(result))



if (myQuery and not resultsQ):
    result["items"].append({
    "title": "No matches",
    "subtitle": "Try a different query",
    
    
    "icon": {

            "path": "icons/Warning.png"
        }
    })
    
    print (json.dumps(result))
            










