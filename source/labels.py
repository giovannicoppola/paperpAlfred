#!/usr/bin/env python3
# v1.0 giovanni, March 2021, from @deanishe tutorial
# v2.0 Feb 2022 - Updated for Python3

from common import browse

browse(table='Labels', name_col='label', total_col='totalLabel',
       id_col='LabelID', summary_col='summaryLabel',
       icon='icons/icon_label.png', source_var='label', id_var='myLabelID')
