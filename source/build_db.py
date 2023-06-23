#!/usr/bin/python3 
# -*- coding: utf-8 -*-
#
# Rebuilding the database
# rewritten script
#
# previously created on Sunday, February 28, 2021
# March 2022 updated to Python3, eliminated dependencies

#Note it currently fails if none of the references are in folders. will need to fix

import json
import sqlite3
import re
import sys
import collections

def log(s, *args):
    if args:
        s = s % args
    print(s, file=sys.stderr)



	
def importingCompleteLibrary (myFile,mydatabase):  # to import complete library before filtering, not used here
    ## reading JSON data in
    with open(myFile, "r") as read_file:
        json_data = json.load(read_file)


    ## getting the list of columns (not all the records have the same columns, nor we can assume that for future dicts)
    # thanks to https://www.codeproject.com/Tips/4067936/Load-JSON-File-with-Array-of-Objects-to-SQLite3-On
    column_list = []
    column = []
    for data in json_data:
        
        column = list(data.keys())
        for col in column:
            if col not in column_list:
                column_list.append(col)



    value = []
    values = [] 
    for data in json_data:
        for i in column_list:
            value.append(str(dict(data).get(i)))   
        values.append(list(value)) 
        value.clear()
        
    create_statement = "create table if not exists myLibrary ({0})".format(" text,".join(column_list))
    insert_statement = "insert into myLibrary ({0}) values (?{1})".format(",".join(column_list), ",?" * (len(column_list)-1))
    drop_statement = "DROP TABLE IF EXISTS myLibrary"  
    # execution	
    db=sqlite3.connect(mydatabase)
    c = db.cursor()   
    c.execute(drop_statement)
    c.execute(create_statement)
    c.executemany(insert_statement , values)
    values.clear()
    db.commit()


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



def createLibrary (myLibrary):

    from config import INDEX_DB    
## reading JSON data in
    with open(myLibrary, "r") as read_file:
        mydata = json.load(read_file)
    
    
### creating a second JSON with a subset of the fields, plus some formatted fields

    #list of elements to get from original JSON
    mySubsetFields = {'title','published','abstract','issue','author','pages','citekey','journal','volume','pmid','labelsNamed','foldersNamed','labels','folders','attachments','subfolders','gdrive_id','_id','pubtype','kind'}    

    # creating the subset (mySubset object)
    mySubset = []
    for item in mydata:
        my_dict={}
        if item['incomplete']==1: ## skipping incomplete items
            continue

        for myfield in mySubsetFields:
            if myfield in item:
                my_dict[myfield]=item.get(myfield)
        mySubset.append(my_dict)

    #combining the authors in authorBlock
    for item in mySubset:
        #log (item['_id'])
        #declaration block, and defaults
        authorBlock =''
        labelBlock =''
        labelIDBlock =''
        folderIDBlock =''
        first =''
        last =''
        folderBlock =''
        myFileName =''
        item.setdefault('pmid', '-')
        item.setdefault('citekey', '-')
        item.setdefault('journal', '-')
        item.setdefault('published', '-')
        item.setdefault('abstract', '')
        item.setdefault('label', '')
        item.setdefault('author', '')
        item.setdefault('issue', '')
        item.setdefault('pages', '')
        item.setdefault('fileName', '')
        item.setdefault('gdrive_id', '')
        item.setdefault('_id', '')
        item.setdefault('pdfFlag', ' ')
        item.setdefault('type', '')
        
        

        # stripping dots from journal names
        item['journal'] = re.sub(r'\.', '', item['journal'])

        for myAuthor in item['author']:
            if myAuthor['formatted'] == item['author'][-1]['formatted']:
                authorBlock += myAuthor['formatted']
            else:
                authorBlock += myAuthor['formatted']+', '
        firstAuthorLN=''
        lastAuthorLN=''
        
        if (len(item['author'])) == 0:
            if ('last' in item['author']):
                firstAuthorLN= item['author']['last'] 
        if (len(item['author'])) > 0:
            if ('last' in item['author'][0]):
                firstAuthorLN= item['author'][0]['last']
            
            if ('last' in item['author'][-1]):
                lastAuthorLN = item['author'][-1]['last']
            if ('year' in item['published'] and item['published']['year'] is not None):
                pubYear = item['published']['year']
            else:
                pubYear = "-"
        
        item.update({'first':firstAuthorLN}) 		
        item.update({'last':lastAuthorLN}) 		

        item.update({'year':pubYear}) 		
        myJournal = item['journal']

        # assigning publication type
        myType=item['pubtype']
        myKinds = ['Commentary','Review','News']
        if 'kind' in item:
            if item['kind'] in myKinds:
                myType=item['kind']
        item.update({'type':myType})



        # flattening labels
        for myLabel in item['labelsNamed']:
            if myLabel == item['labelsNamed'][-1]:
                labelBlock += myLabel
            else:
                labelBlock += myLabel+','	
        item.update({'label':labelBlock}) 		

        # flattening labelIDs
        for myLabel in item['labels']:
            if myLabel == item['labels'][-1]:
                labelIDBlock += myLabel
            else:
                labelIDBlock += myLabel+','	
        item.update({'labelID':labelIDBlock}) 		


    # flattening folders
        for myFolder in item['foldersNamed']:
            if myFolder == item['foldersNamed'][-1]:
                folderBlock += myFolder
            else:
                folderBlock += myFolder +','	
        item.update({'folder':folderBlock}) 		

    # flattening folderIDs
        for myFolder in item['folders']:
            if myFolder == item['folders'][-1]:
                folderIDBlock += myFolder
            else:
                folderIDBlock += myFolder +','	
        item.update({'folderID':folderIDBlock}) 	

        # PDF name or search string
        if (len(item['attachments'])) >0:
            
            # checking source_filename
            if item['attachments'][0]['source_filename'] == "[article_pdf].pdf":
                myFilename = item['attachments'][0]['filename']
            else:
                myTitle=item['title']
                myFilename = firstAuthorLN + '*' + myTitle[0:30]+ '*'
                # search string including the first author and the first 30 characters of the title. should work in most cases. 
            
            # eliminating extra space after ellipsis. another option is to always take the first 30 chars of title
            myFilename = myFilename.replace("...  ", "... ")
            
            # escaping exclamation point in title??
            #myFilename = myFilename.replace("!", "\!")

            item.update({'fileName':myFilename})
            item.update({'pdfFlag':'📜'}) 
            
            # storing google drive ID
            if ('gdrive_id' in item['attachments'][0]):
                myGDrive_ID = item['attachments'][0]['gdrive_id']
                item.update({'gdrive_id':myGDrive_ID})	
            




    # compiling the subtitle	
        #log (f"{firstAuthorLN}-{lastAuthorLN}, {myJournal} {pubYear}")
        subtitle = f"{firstAuthorLN}-{lastAuthorLN}, {myJournal} {pubYear}"
        
        item.update({'subtitle':subtitle}) 	


        

        authorBlock = authorBlock+'.'
        ## generating full reference style used is with PMID, can be changed, or maybe I can have a couple of styles, not sure it is worth creating a universal solution
        fullRef = authorBlock + ' ' + item['title']+'. '+item['journal'] + ' ' + pubYear+';'+item['issue']+':'+item['pages']+'. PMID: '+item['pmid']
        item.update({'fullReference':fullRef}) 	




# generating label lists and file type counts (counting pub types for each label)
    # thanks to Alain T, StackExchange user:5237560 (https://nebularena.wordpress.com)

    counters = {dd['type']:0 for dd in mySubset if 'type' in dd} # if types not fixed
    counters['Total'] = 0
    counters['labelID'] = ''
    myOutput = dict()

    for item in mySubset:     # go through dictionary list
        myLabels = item['label'].split(",")
        myLabelIDs = item['labelID'].split(",")
        
        itemType = item.get('type',None) # get the type
        
        lcc=-1 #label count
        for labell in myLabels: # go through labels list
            lcc += 1 
            if labell:
                if labell in myOutput:
                    labelCounts = myOutput[labell] #if a label exists, get the current type counts
                else:
                    myOutput[labell] = labelCounts = dict (counters)
                    labelCounts['labelID'] = myLabelIDs[lcc] #fetches the label ID
                if itemType : labelCounts[itemType] += 1 # count items for type if any
                labelCounts['Total'] += 1
    
    myFinalCount = []
    for key, val in myOutput.items():
        mySubText = ''
        val =  {k.lower(): v for k, v in val.items()}  #converting to lowercase
        val =  {k.replace('pp_', ''): v for k, v in val.items()} # eliminating pp
        
        
        # this section below is to convert previous code and could be made better
        valSub = {k: val[k] for k in set(list(val.keys())) - set(['labelid','total'])}  #subsetting the type totals, so that they can be sorted
        valSub = sorted(valSub.items(), key=lambda x: x[1], reverse=True) # sorting toitals for each type
        valSub = collections.OrderedDict(valSub) #converting back into a dictionary
        

        for key2, val2 in valSub.items(): 
            if val2 != 0 and key2 != 'total' and key2 != 'labelid':  #formatting all fields except total and labelID
                myText = '{} ({}) '.format(key2, val2)
                mySubText = mySubText + myText
        myFinalCount.append ({
                'label': key,
                'totalLabel': val['total'],
                'LabelID': val['labelid'],
                'summaryLabel': mySubText
                    })
            
    # creating the table in the sqlite database
    
    JSONtoDB (myJSON=myFinalCount,myTable='Labels', mydatabase=INDEX_DB)


# generating folder list and counts

    counters = {dd['type']:0 for dd in mySubset if 'type' in dd} # if types not fixed
    counters['Total'] = 0
    counters['folderID'] = ''
    myOutput = dict()

    for item in mySubset:     # go through dictionary list
        myLabels = item['folder'].split(",")
        myLabelIDs = item['folderID'].split(",")
        itemType = item.get('type',None) # get the type
        
        lcc=-1 #label count
        for labell in myLabels: # go through labels list
            lcc += 1 
            if labell:
                if labell in myOutput:
                    labelCounts = myOutput[labell] #if a folder exists, get the current type counts
                else:
                    myOutput[labell] = labelCounts = dict (counters)
                    labelCounts['folderID'] = myLabelIDs[lcc] #fetches the folder ID
                if itemType : labelCounts[itemType] += 1 # count items for type if any
                labelCounts['Total'] += 1

    #print (myOutput)
    myFinalCount = []
    for key, val in myOutput.items():
        mySubText = ''
        val =  {k.lower(): v for k, v in val.items()}
        val =  {k.replace('pp_', ''): v for k, v in val.items()}
        
        # this section below is to convert previous code and could be made better
        valSub = {k: val[k] for k in set(list(val.keys())) - set(['folderid','total'])}  #subsetting the type totals, so that they can be sorted
        valSub = sorted(valSub.items(), key=lambda x: x[1], reverse=True) # sorting toitals for each type
        valSub = collections.OrderedDict(valSub) #converting back into a dictionary
        
        for key2, val2 in valSub.items(): 
        
            if val2 != 0 and key2 != 'total' and key2 != 'folderid':
                myText = '{} ({}) '.format(key2, val2)
                mySubText = mySubText + myText
        myFinalCount.append ({
        'folder': key,
        'totalFolder': val['total'],
        'FolderID': val['folderid'],
        'summaryFolder': mySubText
            })

    # creating the table in the sqlite database
    JSONtoDB (myJSON=myFinalCount,myTable='Folders', mydatabase=INDEX_DB)

        

    ### creating a list of unique types
    myTypeList=[]
    for item in mySubset:
        myTypes = item['type'].split(",")
        for myCurrType in myTypes:
            if myCurrType:
                myTypeList.append(myCurrType)
            

    myTypeList = [x.replace('PP_', '') for x in myTypeList]
    myTypeList = [x.replace('_', ' ') for x in myTypeList]
    myTypeList = [each_string.capitalize() for each_string in myTypeList]

    myTypeSummary = collections.Counter(myTypeList)	
    
    myFinalCount = []
    for key, val in myTypeSummary.items():
        myFinalCount.append ({
            'type': key,
            'totalType': val
            
                })
    
    
    JSONtoDB (myJSON=myFinalCount,myTable='Types', mydatabase=INDEX_DB)





    # preparing the final output: excluding items no longer needed
    myFinalSubset = []
    toExclude = ['author','published','issue','pages','volume','labelsNamed','foldersNamed','labels','folders','attachments','subfolders','pubtype','kind']

    for item in mySubset:
        
        myItem={}
        myItem = {k: item[k] for k in item.keys() - toExclude}
        myFinalSubset.append(myItem)

    JSONtoDB (myJSON=myFinalSubset,myTable='papers', mydatabase=INDEX_DB)
     

        
        

    # if os.path.exists(INDEX_DB):
    #     os.remove(INDEX_DB)
    # # deleting the existing index db, so the papers.py script is forced to rebuild




#if __name__ == "__main__":
    #importingLibrary(LIBRARY_FILE, MY_DATABASE)
    #createLibrary (LIBRARY_FILE)
