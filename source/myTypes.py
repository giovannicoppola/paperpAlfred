#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# giovanni, March 2021, from @deanishe's template
# Modified from books, to show paper types for filtering
# Tuesday, March 15, 2022 - update to Python3

from common import browse

browse(table='Types', name_col='type', total_col='totalType',
       id_col=None, summary_col=None,
       icon='icons/icon_type.png', source_var='type', id_var='myTypeID')
