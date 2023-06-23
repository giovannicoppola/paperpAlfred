#!/usr/bin/python3 
# -*- coding: utf-8 -*-
#
# Rebuilding the database
# rewritten script
#
# previously created on Sunday, February 28, 2021
# March 2022 updated to Python3, eliminated dependencies

import json



	
def importingCompleteLibrary (myFile):  # to import complete library before filtering, not used here
    ## reading JSON data in
    with open(myFile, "r") as read_file:
        json_data = json.load(read_file)
    
    mySubset = [x for x in json_data if "labelsNamed" in x and 'interesting' in x['labelsNamed']]
    
    with open("demo_library.json", "w") as f:
        json.dump(mySubset, f,indent=4)

myFile = 'path/to/library'
importingCompleteLibrary(myFile)


