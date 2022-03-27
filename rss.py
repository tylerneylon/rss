#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    rss.py

    A simple tool to create and maintain rss feed files.
    This is an RSS *writer*, not a reader.

    Usage:

        # When you have a new post directory, cd into the directory of that
        # post and run this, then edit fields in the new rss_items.json file:
        rss.py post

        # When you add a new post to a directory with an existing rss_items.json
        # file; similar you will need to edit fields after you run this:
        rss.py append
"""


# __________________________________________________________________________
# Imports

import json
import os
import sys
import xml.etree.ElementTree as ET

from datetime import datetime
from email    import utils


# __________________________________________________________________________
# Constants

ITEMS_FILENAME = 'rss_items.json'


# __________________________________________________________________________
# Functions

def show_usage_and_exit():
    exec_name = os.path.basename(sys.argv[0])
    print(__doc__.replace('rss.py', exec_name))
    exit(0)

# In the future, this may take an optional argument with some indication of
# the timestamp for which we provide a date string.
def get_date_str():
    return utils.format_datetime(datetime.now().astimezone())

def make_new_post_obj():
    return {
            'title'      : 'TITLE',
            'link'       : 'URL',  # TODO
            'description': 'DESCRIPTION',
            'author'     : 'AUTHOR',
            'pubDate'    : get_date_str()
    }

def make_new_post_json_file():
    if os.path.exists(ITEMS_FILENAME):
        print(f'Error: The file {ITEMS_FILENAME} already exists.')
        print('Use the append command to add a post to an existing file.')
        exit(1)
    obj = make_new_post_obj()
    with open(ITEMS_FILENAME, 'w') as f:
        json.dump([obj], f, indent=4, sort_keys=True)
    print(f'Wrote template json file to {ITEMS_FILENAME}')


# __________________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2:
        show_usage_and_exit()

    action = sys.argv[1]

    if action == 'post':
        make_new_post_json_file()

