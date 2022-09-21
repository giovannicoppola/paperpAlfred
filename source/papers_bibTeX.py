#!/usr/bin/env python3
# Search Paperpile library using Alfred
# simplified version for BibTeX automatic export
# Partly cloudy ⛅️  🌡️+73°F (feels +77°F, 55%) 🌬️↗4mph 🌘 Wed Sep 21 16:59:51 2022



import sys
import os
import json
import sqlite3



from config import INDEX_DB, MAXRES, BIBTEX_FILE, TIMESTAMP

from build_db import *

try: 
    
    new_time = int(os.path.getmtime(BIBTEX_FILE))
    
except:   #error if the library file is missing
    result= {"items": [{
    "title": "Library file missing!",
    "subtitle": "cannot locate the Paperpile BibTeX library file",
    "arg": "",
    "icon": {

            "path": "icons/Warning.png"
        }
    }]}
    print (json.dumps(result))
    sys.exit("Script aborted – file missing")

if not os.path.exists(TIMESTAMP):
    with open(TIMESTAMP, "w") as f:
        f.write(str(new_time))
        f.close
    createLibrary (LIBRARY_FILE)
    


## checking the timestamp
with open(TIMESTAMP) as f:
    old_time = int(f.readline()) #getting the old UNIX timestamp
    f.close


if new_time != old_time:
    
    with open(TIMESTAMP, "w") as f:
        f.write(str(new_time))
        f.close
    
    createLibrary (LIBRARY_FILE)
    

# getting the user query
myQuery=sys.argv[1]

result = {"items": []}

orderSel = "DESC"

if "--a" in myQuery:
    orderSel = "ASC"
    myQuery = myQuery.replace (' --a','')


# Search!
db = sqlite3.connect(INDEX_DB)
cursor = db.cursor()


try:
    
    cursor.execute("""SELECT _id,abstract, citekey, fileName, first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year FROM
                        (SELECT papers
                            AS r, _id, abstract, citekey, fileName,first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year
                            FROM papers WHERE papers MATCH ?)
                        ORDER BY year """ +orderSel + """ LIMIT """ + MAXRES + """ """, (myQuery + '*',))
    
    
    
    
    results = cursor.fetchall()

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

    


if (not myQuery):
    introDial= {"items": [{
        "title": "Welcome to paperpAlfred 👋",
        "subtitle": "Enter a query or ↩️ for help",
        "valid": True,
        "arg": "ShowHelpWindow",
        "icon": {
            "path": "icons/paperpAlfred_ico.png"
            }
            }]}
    print (json.dumps(introDial))
    
    
    

    


# Output results to Alfred
if (myQuery and results):
    myResLen = str(len (results))
    countR=1
    for (_id, abstract, citekey, fileName, first, folder,folderID, fullReference, journal, label,labelID, last, pdfFlag, pmid, subtitle, title, gdrive_id, type, year) in results:
        aut_journ =  str(countR) + '/' + myResLen +  pdfFlag + subtitle + " 🏷" + label
        

        result["items"].append({
            "title": title,
            "subtitle": aut_journ,
            "variables": {
                "myFileName": fileName,
                "FullReference": fullReference,
                "shortPMID": subtitle+" "+pmid,
                "myAbstract": abstract,
                "myCitekey": citekey,
                "gdrive_id": gdrive_id,
                "paperpileID": _id
            },
            "valid": True,
            
            "icon": {

                    "path": "icons/paperpAlfred_ico.png"
                }
            })
        countR += 1  


    print (json.dumps(result))
     



if (myQuery and not results):
    result= {"items": [{
    "title": "No matches",
    "subtitle": "Try a different query",
    
    "arg": "",
    "icon": {

            "path": "icons/Warning.png"
        }
    }]}
    
    print (json.dumps(result))
    
    


