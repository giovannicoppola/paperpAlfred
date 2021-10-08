#!/usr/bin/env python
# encoding: utf-8
#
# Script to rebuild the database
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on Sunday, February 28, 2021
# script is migrated from json2tsv.py in the scripts folder

"""Common settings."""

from __future__ import unicode_literals

import sys
import os
import json
import re
import csv
import collections

from workflow import Workflow, ICON_INFO, ICON_WARNING
log = None


wf = Workflow()

from config import LABELS_OUT, DATA_FILE, INDEX_DB, FOLDERS_OUT, TYPES_OUT, LIBRARY_FILE





def main(wf):

	
	
	
	## reading JSON data in
	with open(LIBRARY_FILE, "r") as read_file:
		mydata = json.load(read_file)

	### creating a second JSON with a subset of the fields

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
		#print (item['pmid'])
		if (len(item['author'])) == 0:
			if ('last' in item['author']):
				firstAuthorLN= item['author']['last'] 
		if (len(item['author'])) > 0:
			if ('last' in item['author'][0]):
				firstAuthorLN= item['author'][0]['last']
			
			if ('last' in item['author'][-1]):
				lastAuthorLN = item['author'][-1]['last']
			if ('year' in item['published']):
				pubYear = item['published']['year']
		
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
		subtitle = firstAuthorLN +"-"+ lastAuthorLN + ", " + myJournal + " " + pubYear
		item.update({'subtitle':subtitle}) 	


		

		authorBlock = authorBlock+'.'
		## generating full reference style used is with PMID, can be changed, or maybe I can have a couple of styles, not sure it is worth creating a universal solution
		fullRef = authorBlock + ' ' + item['title']+'. '+item['journal'] + ' ' + pubYear+';'+item['issue']+':'+item['pages']+'. PMID: '+item['pmid']
		item.update({'fullReference':fullRef}) 	




# generating label list and counts
# counting pub types
# thanks to Alain T, StackExchange user:5237560 (https://nebularena.wordpress.com)
	
	counters = {dd['type']:0 for dd in mySubset if 'type' in dd} # if types not fixed
	counters['Total'] = 0
	counters['labelID'] = ''
	myOutput = dict()
	
	for item in mySubset:     # go through dictionary list
		myLabels = item['label'].split(",")
		myLabelIDs = item['labelID'].split(",")
		#print (myLabels)
		itemType = item.get('type',None) # get the type
		#print (itemType)
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


	
	

	myOutputS = sorted(myOutput.items(), key=lambda x: x[1]['Total'], reverse=True)
	myOutputS = collections.OrderedDict(myOutputS)

	items = []
	for key, val in myOutputS.items():
		mySubText = ''
		val =  {k.lower(): v for k, v in val.items()}
		val =  {k.replace('pp_', ''): v for k, v in val.items()}
		val = sorted(val.items(), key=lambda x: x[1], reverse=True)
		val = collections.OrderedDict(val)
		for key2, val2 in val.items(): 
			myItem={}
			
			if val2 != 0 and key2 != 'total' and key2 != 'labelid':
				myText = '{} ({}) '.format(key2, val2)
				mySubText = mySubText + myText
		items.append({
			'title': '{} ({})'.format(key, val['total']),
			'subtitle': mySubText,
			'arg': '{};;{}'.format(key, val['labelid']),
			})

		
	with open(LABELS_OUT, 'w') as fp:
		js = json.dumps({'items': items}, indent=2, separators=(',', ':'))
		fp.write(js)

	

# generating folder list and counts
	
	counters = {dd['type']:0 for dd in mySubset if 'type' in dd} # if types not fixed
	counters['Total'] = 0
	counters['folderID'] = ''
	myOutput = dict()
	
	for item in mySubset:     # go through dictionary list
		myLabels = item['folder'].split(",")
		myLabelIDs = item['folderID'].split(",")
		itemType = item.get('type',None) # get the type
		#print (itemType)
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


	myOutputS = sorted(myOutput.items(), key=lambda x: x[1]['Total'], reverse=True)
	myOutputS = collections.OrderedDict(myOutputS)

	items = []
	for key, val in myOutputS.items():
		mySubText = ''
		val =  {k.lower(): v for k, v in val.items()}
		val =  {k.replace('pp_', ''): v for k, v in val.items()}
		val = sorted(val.items(), key=lambda x: x[1], reverse=True)
		val = collections.OrderedDict(val)
		for key2, val2 in val.items(): 
			myItem={}
			
			if val2 != 0 and key2 != 'total' and key2 != 'folderid':
				myText = '{} ({}) '.format(key2, val2)
				mySubText = mySubText + myText
		items.append({
			'title': '{} ({})'.format(key, val['total']),
			'subtitle': mySubText,
			'arg': '{};;{}'.format(key, val['folderid']),
			})

		
	with open(FOLDERS_OUT, 'w') as fp:
		js = json.dumps({'items': items}, indent=2, separators=(',', ':'))
		fp.write(js)


### creating a list of unique types
	myTypeList=[]
	for item in mySubset:
		myTypes = item['type'].split(",")
		for myCurrType in myTypes:
			if myCurrType is not "":
				myTypeList.append(myCurrType)
			#print (myCurrFolder)	
	
	myTypeList = [x.replace('PP_', '') for x in myTypeList]
	myTypeList = [x.replace('_', ' ') for x in myTypeList]
	myTypeList = [each_string.capitalize() for each_string in myTypeList]

	myTypeSummary = collections.Counter(myTypeList)	
	myTypeSummaryS = sorted(myTypeSummary.items(), key=lambda x: x[1], reverse=True)
	myTypeSummaryS = collections.OrderedDict(myTypeSummaryS)

	w = csv.writer(open(TYPES_OUT, "w"),delimiter=str('\t'))
	for key, val in myTypeSummaryS.items():
	    w.writerow([unicode(key).encode('utf8'), val])


	


	# preparing the final output: excluding items no longer needed
	myFinalSubset = []
	toExclude = {'author','published','issue','pages','volume','labelsNamed','foldersNamed','labels','folders','attachments','subfolders','pubtype','kind'}

	for item in mySubset:
		#print (type(item))
		myItem={}
		myItem = {k: item[k] for k in item.keys() if k not in toExclude}
		# this works in Python3
		#myItem = {k: item[k] for k in item.keys() - {'author'}}
		myFinalSubset.append(myItem)


	
	with open(DATA_FILE, 'wb') as f:
		f.write(u'\ufeff'.encode('utf8')) # BOM (optional...Excel needs it to open UTF-8 file properly)

		keys = myFinalSubset[0].keys()
		w = csv.DictWriter(f,sorted(keys))
		w.writeheader()

		for item in myFinalSubset:
			w.writerow({k:unicode(v).encode('utf8') for k,v in item.items()})
	f.close()
		

		
		

	if os.path.exists(INDEX_DB):
		os.remove(INDEX_DB)
	# deleting the existing index db, so the papers.py script is forced to rebuild

	wf.add_item('Done!', 'Ready to query', icon=ICON_INFO)
	wf.send_feedback()





if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))


