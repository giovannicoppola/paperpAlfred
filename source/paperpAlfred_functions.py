#!/usr/bin/env python3


# Functions for paperpAlfred: 
# log (for logging and debugging)
# checkingTime (to checktimestamps)
# JSONtoDB (to rebuild the database)
# 


import sys
import os
import sqlite3
import time
import bibtexparser 
import re
from config import BIBTEX_FILE, INDEX_DB

#Partly cloudy ⛅️  🌡️+73°F (feels +77°F, 55%) 🌬️↗4mph 🌘 Wed Sep 21 16:59:51 2022
#W38Q3 – 264 ➡️ 100 – 133 ❇️ 232
startTime = time.time()

#from config import TIMESTAMP, INDEX_DB






def build_BibTeX_db (BIBTEX_FILE):
    with open(BIBTEX_FILE) as bibtex_file:
        #bib_database = bibtexparser.load(bibtex_file)
        bib_database = bibtexparser.bparser.BibTexParser(common_strings=True).parse_file(bibtex_file) # this is for the string in the month

    #print(bib_database.entries)

    myJSONlist = (bib_database.entries)

    #formatting the author block
    for myEntry in myJSONlist:
        myAuthors = myEntry['author'].split("and ")
        
        print (f"number of authors: {len(myAuthors)}")
        authorBlock = ''
        
        authorCount = 0
        for eachAuthor in myAuthors:
            authorCount += 1
            if ',' in eachAuthor:
                lastName,firstName = eachAuthor.split(",")
                firstInitials = "".join(item[0].upper() for item in firstName.split())
                #print (f"last name: {lastName}, initials: {firstInitials}")
                #print (f"{lastName} {firstInitials}")
                eachAuthor_name = f"{lastName} {firstInitials}"
            else:
                eachAuthor_name = eachAuthor.strip()
            
            #assigning first and last author
            if authorCount == 1:
                firstAuthor = eachAuthor_name.split()[0]
                myEntry['firstAuthor'] = firstAuthor
                linker = ''
            else:
                linker = ', '
            if authorCount == len (myAuthors):
                lastAuthor = eachAuthor_name.split()[0]
                myEntry['lastAuthor'] = lastAuthor
            
            authorBlock = f"{authorBlock}{linker}{eachAuthor_name}"
            myEntry['authorBlock'] = authorBlock

            #stripping Journal of periods
            myEntry['journal'] = re.sub(r'\.', '', myEntry['journal'])
            #myEntry.update({'journal':re.sub(r'\.', '', myEntry['journal'])})
            
            
        shortRef = f"{firstAuthor}-{lastAuthor}, {myEntry['journal']} {myEntry['year']} {myEntry['pmid']}"
        myEntry['shortRef'] = shortRef
        print (shortRef)

        # strip {}
        if myEntry['title'][0] == "{":
            myEntry['title'] = myEntry['title'][1:] 
        if myEntry['title'][-1] == "}":
            myEntry['title'] = myEntry['title'][:-1] 
        
        if "pages" in myEntry:
            pagesBlock = f":{myEntry['pages']}."
        else:
            pagesBlock = ""

        if "pmid" in myEntry:
            pmidBlock = f" PMID: {myEntry['pmid']}."
        else:
            pmidBlock = ""

        if "volume" not in myEntry:
            myEntry['volume'] = "-"


        fullRef= f"{authorBlock}. {myEntry['title']}. {myEntry['journal']} {myEntry['year']};{myEntry['volume']}{pagesBlock}{pmidBlock}"
        print (fullRef)
            
        

        #print (authorBlock)
        #output = "".join(item[0].upper() for item in input.split())
        
        
        #Huang AY, Taylor AMW, Ghogha A, Pribadi M, Wang Q, Kim TSJ, Cahill CM, Coppola G, Evans CJ. Genetic and functional analysis of a Pacific hagfish opioid system. J Neurosci Res 2022;1:19-34. PMID: 32830380
        
    #myJSON = json.dumps(bib_database.entries)


    JSONtoDB (myJSONlist, "BibTeX_db", INDEX_DB)


def log(s, *args):
    if args:
        s = s % args
    print(s, file=sys.stderr)



def checkingTime (dirname):
## Checking if the index needs to be rebuilt
# one other option was to add everything to a list then choose the max. 
# advantage: I already have the max to add it to the timestamp
# disadvage: needs to go through all dirs, while with the other method you can break as soon one is more recent than the timestamp

    ## checking the timestamp
    with open(TIMESTAMP) as f:
        old_time = int(f.readline()) #getting the old UNIX timestamp
        f.close

    

    for (idx,d) in enumerate(dirs): # goes through each directory looking for a plist file. idx is a counter from enumerate, d is the directory (and plist file) name
        try:
            myTime= (int(os.path.getmtime(myPlist)))
            #log (idx)
            # this should be faster because it breaks when it finds one
            if myTime >= old_time:
                log ("found an updated plist file, rebuilding the database")
                #fetching all the plists and rebuilding the database
                return "toBeUpdated"
        except:
            continue
    executionTime = (time.time() - startTime)
    log ("time to check timestamps: "+ str(executionTime))
    log ("database uptodate")

    
    # updating the timestamp
    with open(TIMESTAMP, "w") as f:
        f.write(str(round (startTime))) # update the timestamp
    f.close
                    
                
    
            
        
     
    


def JSONtoDB (myJSON,myTable, mydatabase):
    column_list = []
    column = []
    for data in myJSON:
        
        column = list(data.keys())
        for col in column:
            if col not in column_list:
                column_list.append(col)

    value = []
    values = [] 
    for data in myJSON:
        for i in column_list:
            value.append(str(dict(data).get(i)))   
        values.append(list(value)) 
        value.clear()
        
    
    
    create_statement = "create VIRTUAL table " + myTable + " USING FTS3 ({0})".format(" text,".join(column_list))
      
    insert_statement = "insert into " + myTable + " ({0}) values (?{1})".format(",".join(column_list), ",?" * (len(column_list)-1))    
    drop_statement = "DROP TABLE IF EXISTS "+ myTable  

    # execution	
    db=sqlite3.connect(mydatabase)
    c = db.cursor()   
    c.execute(drop_statement)
    c.execute(create_statement)
    c.executemany(insert_statement , values)
    values.clear()
    db.commit()





build_BibTeX_db (BIBTEX_FILE)
