#!/usr/bin/env python3


# Functions for paperpAlfred: 
# log (for logging and debugging)

# JSONtoDB (to rebuild the database)
# 


import sys
import os
import sqlite3
import time
import bibtexparser 
import re
#from config import INDEX_DB

#Partly cloudy ⛅️  🌡️+73°F (feels +77°F, 55%) 🌬️↗4mph 🌘 Wed Sep 21 16:59:51 2022
#W38Q3 – 264 ➡️ 100 – 133 ❇️ 232
startTime = time.time()

INDEX_DB = "/Users/giovanni/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/giovanni.paperpAlfred/index.db"


def build_BibTeX_db (BIBTEX_FILE):
    with open(BIBTEX_FILE) as bibtex_file:
        #bib_database = bibtexparser.load(bibtex_file)
        bib_database = bibtexparser.bparser.BibTexParser(common_strings=True).parse_file(bibtex_file) # this is for the string in the month

    #print(bib_database.entries)

    myJSONlist = (bib_database.entries)

    #formatting the author block
    for myEntry in myJSONlist:
        for myEntry in myJSONlist:
            if "author" in myEntry:
                myAuthors = myEntry['author'].split("and ")
            
                #print (f"number of authors: {len(myAuthors)}")
                authorBlock = ''
                
                authorCount = 0
                for eachAuthor in myAuthors:
                    authorCount += 1
                    #print (eachAuthor)
                    if ',' in eachAuthor:
                        lastName,firstName = eachAuthor.split(",",1)
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
        if "journal" in myEntry:
            myEntry['journal'] = re.sub(r'\.', '', myEntry['journal'])
        else:
            myEntry['journal'] = ''
                  
        
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
            myEntry['pmid'] = ''

        if "volume" not in myEntry:
            myEntry['volume'] = "-"

        if "annot" not in myEntry:
            myEntry['annot'] = ""

        shortRef = f"{firstAuthor}-{lastAuthor}, {myEntry['journal']} {myEntry['year']} {myEntry['pmid']}"
        myEntry['shortRef'] = shortRef
        #print (shortRef)

        fullRef = f"{authorBlock}. {myEntry['title']}. {myEntry['journal']} {myEntry['year']};{myEntry['volume']}{pagesBlock}{pmidBlock}"
        myEntry['fullRef'] = fullRef
        #print (fullRef)
        # renaming problematic names
        if "ID" in myEntry:
            myEntry['myID'] = myEntry['ID']
            del myEntry['ID']

        if "file" in myEntry:
            myEntry['myFile'] = myEntry['file']
            del myEntry['file']
            
            
        

        #print (authorBlock)
        #output = "".join(item[0].upper() for item in input.split())
        
        
        #Huang AY, Taylor AMW, Ghogha A, Pribadi M, Wang Q, Kim TSJ, Cahill CM, Coppola G, Evans CJ. Genetic and functional analysis of a Pacific hagfish opioid system. J Neurosci Res 2022;1:19-34. PMID: 32830380
        
    #myJSON = json.dumps(bib_database.entries)


    JSONtoDB (myJSONlist, "BibTeX_db", INDEX_DB)


def log(s, *args):
    if args:
        s = s % args
    print(s, file=sys.stderr)



    
            

     
    


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






build_BibTeX_db ("/Users/giovanni/Library/CloudStorage/GoogleDrive-giovannicoppola@gmail.com/My Drive/paperpile.bib")