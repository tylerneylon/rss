#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    rss.py

    A simple tool to create and maintain rss feed files.
    This is an RSS *writer*, not a reader.

    Usage:

        # When you have a new post, cd into the directory of that post and run
        # this, then edit the fields in the rss_items.json file:
        rss.py post [filename_of_post_html]

        # Run this command to designate the local root directory of your
        # website. This creates a template rss_root.json file for you to edit,
        # and this root directory is used to infer what the url paths will be to
        # posts in subdirectories:
        rss.py root

        # Run this command to verify that rss_{root,items}.json files are
        # correctly formatted. If you run this in the root directory without any
        # parameters, it checks the validity of all rss_{root,items}.json files
        # recursively:
        rss.py check [json_filename]

"""


# __________________________________________________________________________
# Imports

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from datetime import datetime
from email    import utils


# __________________________________________________________________________
# Globals and Constants

ITEMS_FILENAME = 'rss_items.json'

# Escape codes for terminal writing. These are set up in init().
red    = None
yellow = None
normal = None

NORMAL  = 0
WARNING = 1
ERROR   = 2

DEFAULT_ITEM_VALUES = {
    'title'      : 'TITLE',
    'link'       : 'URL',
    'description': 'DESCRIPTION',
    'author'     : 'AUTHOR',
    'pubDate'    : 'DATE'
}


# __________________________________________________________________________
# Functions

def init():
    global red, yellow, normal
    red    = subprocess.check_output('tput setaf 1'.split())
    yellow = subprocess.check_output('tput setaf 3'.split())
    normal = subprocess.check_output('tput sgr0'.split())

def show(level, msg):
    if level == WARNING:
        sys.stdout.buffer.write(yellow + b'zomg warning: ' + normal)
    if level == ERROR:
        sys.stdout.buffer.write(red    + b'zomg error: '   + normal)
    print(msg)

def show_usage_and_exit():
    exec_name = os.path.basename(sys.argv[0])
    print(__doc__.replace('rss.py', exec_name))
    exit(0)

# In the future, this may take an optional argument with some indication of
# the timestamp for which we provide a date string.
def get_date_str():
    return utils.format_datetime(datetime.now().astimezone())

def make_new_post_obj():
    defaults = DEFAULT_ITEM_VALUES
    return {
            'title'      : defaults['TITLE'],
            'link'       : defaults['URL'],  # TODO
            'description': defaults['DESCRIPTION'],
            'author'     : defaults['AUTHOR'],
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

def check_file(filepath):
    # TODO Add validity check for rss_root.json.
    basename = os.path.basename(filepath)
    if basename != ITEMS_FILENAME:
        show(WARNING, f'Invalid rss filename: {basename}')
    else:
        with open(filepath) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                show(ERROR, f'Unable to parse the JSON in file {filepath}')
                print(err)
        required_fields = ['title', 'link', 'description', 'author', 'pubDate']
        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    show(ERROR, f'Missing field in item {i}: {field}')
                elif item[field] == DEFAULT_ITEM_VALUES[field]:
                    show(WARNING, f'Default value in item {i}: {field}')
                    print('You probably want to customize before publishing')


# __________________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2:
        show_usage_and_exit()

    init()
    action = sys.argv[1]

    if action == 'post':
        make_new_post_json_file()
    elif action == 'check':
        if len(sys.argv) < 3:
            pass  # TODO Handle the no-filename case.
            exit(0)
        else:
            filename = sys.argv[2]
            check_file(filename)
    else:
        show(ERROR, f'Unrecognized action: {action}')

