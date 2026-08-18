#!/usr/bin/env python3
# v1.0 giovanni, March 2021, from @deanishe tutorial
# v2.0 Feb 2022 - Updated for Python3

from common import browse

browse(table='Folders', name_col='folder', total_col='totalFolder',
       id_col='FolderID', summary_col='summaryFolder',
       icon='icons/icon_folder.png', source_var='folder', id_var='myFolderID')
