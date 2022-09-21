#!/usr/bin/python3 
#
# using the BibTeX background export

#
#New York – Partly cloudy ⛅️  🌡️+66°F (feels +66°F, 68%) 🌬️↘4mph 🌘 Wed Sep 21 06:23:37 2022
#W38Q3 – 264 ➡️ 100 – 191 ❇️ 173

import bibtexparser # did not work, error with non-quoted entries (eg month)
import json
import sqlite3
#BIBTEX_FILE = "/Users/giovanni/Library/CloudStorage/GoogleDrive-giovannicoppola@gmail.com/My Drive/Tsu_ASO-RNAi.bib"
BIBTEX_FILE = "/Users/giovanni/Library/CloudStorage/GoogleDrive-giovannicoppola@gmail.com/My Drive/Tsu_Dementia.bib"
INDEX_DB = "indexTEST.db"


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



with open(BIBTEX_FILE) as bibtex_file:
    #bib_database = bibtexparser.load(bibtex_file)
    bib_database = bibtexparser.bparser.BibTexParser(common_strings=True).parse_file(bibtex_file) # this is for the string in the month

#print(bib_database.entries)

myJSONlist = (bib_database.entries)

for myEntry in myJSONlist:
    myAuthors = myEntry['author'].split("and ")
    print (myAuthors)
    authorBlock = ''
    linker = ''
    for eachAuthor in myAuthors:
        lastName,firstName = eachAuthor.split(",")
        firstInitials = "".join(item[0].upper() for item in firstName.split())
        print (f"last name: {lastName}, initials: {firstInitials}")
        print (f"{lastName} {firstInitials}")
        if authorBlock != '':
            linker = ', '
        authorBlock = f"{authorBlock}{linker}{lastName} {firstInitials}"

    print (authorBlock)
    #output = "".join(item[0].upper() for item in input.split())
    
    
    
    
#myJSON = json.dumps(bib_database.entries)


#JSONtoDB (myJSONlist, "myTTable", INDEX_DB)










