#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    rss.py

    A simple tool to create and maintain rss feed files.
    This is an RSS *writer*, not a reader.

    Usage:

        # When you have a new post, cd into the directory of that post and run
        # this, then edit the fields in the rss_items.json file:

        rss.py post [filename_of_post_html_file]


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

import copy
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from datetime import datetime
from email    import utils
from pathlib  import Path

# XXX
import traceback


# __________________________________________________________________________
# Globals and Constants

ITEMS_FILENAME = 'rss_items.json'
ROOT_FILENAME  = 'rss_root.json'

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
DEFAULT_ROOT_VALUES = {
    'title':       'TITLE',
    'link':        'LINK',
    'description': 'DESCRIPTION'
}

# Return values from check_file().
GOOD = 'good'
DEFAULT_PRESENT = 'default_present'
# ERROR re-uses the above global constant.


# __________________________________________________________________________
# Functions

def init():
    global red, yellow, normal
    red    = subprocess.check_output('tput setaf 1'.split())
    yellow = subprocess.check_output('tput setaf 3'.split())
    normal = subprocess.check_output('tput sgr0'.split())

def show(level, msg):
    if level == WARNING:
        sys.stdout.buffer.write(yellow + b'zomg warning: '  + normal)
    if level == ERROR:
        sys.stdout.buffer.write(red    + b'ruh roh error: ' + normal)
    print(msg)
    if level == ERROR:
        traceback.print_stack()

def show_usage_and_exit():
    exec_name = os.path.basename(sys.argv[0])
    print(__doc__.replace('rss.py', exec_name))
    exit(0)

# In the future, this may take an optional argument with some indication of
# the timestamp for which we provide a date string.
def get_date_str():
    return utils.format_datetime(datetime.now().astimezone())

def make_new_post_obj():
    obj = copy.copy(DEFAULT_ITEM_VALUES)
    # TODO customize the `link` as much as possible.
    obj['pubDate'] = get_date_str()
    return obj

# Try to infer the path of the URL for the current directory. This succeeds if
# we can locate an rss_root.json file in this directory or a parent directory,
# in which case that root file is used to determine the publication root dir. In
# case we can't find the root, then this returns the empty string.
def guess_path(filename=None):
    curr_dir = Path.cwd()
    while True:
        print(f'curr_dir = {curr_dir}')  # XXX
        root_filepath = curr_dir / ROOT_FILENAME
        if root_filepath.exists():
            print(f'Found root file at {root_filepath}')  # XXX
            with open(root_filepath) as f:
                data = json.load(f)
            root_dir = curr_dir / data['rootDir']
            print(f'Found root dir as {root_dir}')  # XXX
            basepath = Path.cwd() if not filename else Path.cwd() / filename
            rel_path_str = str(basepath.relative_to(root_dir))
            if rel_path_str == '.':
                rel_path_str = ''
            return '/' + rel_path_str
        if curr_dir.parent == curr_dir:
            return filename
        curr_dir = curr_dir.parent

def add_new_post(filename=''):
    if os.path.exists(ITEMS_FILENAME):
        result = check_file(ITEMS_FILENAME, do_print=False)
        if result == ERROR:
            show(ERROR, 'Can\'t append to json file due to an error:')
            check_file(ITEMS_FILENAME)  # To print the error.
            exit(1)
        elif result == DEFAULT_PRESENT:
            show(ERROR, 'I don\'t append to files with uncustomized values:')
            check_file(ITEMS_FILENAME)  # To print the warning.
            exit(1)
        else:
            with open(ITEMS_FILENAME) as f:
                data = json.load(f)
    else:
        data = []
    obj = make_new_post_obj()
    guessed_path = guess_path(filename)
    if guessed_path:
        obj['link'] = guessed_path
    with open(ITEMS_FILENAME, 'w') as f:
        json.dump(data + [obj], f, indent=4, sort_keys=True)
    print(f'Wrote template post data to {ITEMS_FILENAME}')

def make_root_json_file():
    if os.path.exists(ROOT_FILENAME):
        show(ERROR, f'Root file already exists: {ROOT_FILENAME}')
    else:
        obj = copy.copy(DEFAULT_ROOT_VALUES)
        obj['rootDir'] = '.'
        obj['rssFilename'] = 'feed'
        with open(ROOT_FILENAME, 'w') as f:
            json.dump(obj, f, indent=4)
        print(f'Wrote template root data to {ROOT_FILENAME}')

# This returns 'good', 'default_present', or 'error'.
def check_file(filepath, do_print=True):
    ret_value = GOOD
    # TODO Add validity check for rss_root.json.
    basename = os.path.basename(filepath)
    if basename == ITEMS_FILENAME:
        with open(filepath) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                if do_print:
                    show(ERROR, f'Unable to parse the JSON in file {filepath}')
                    print(err)
                ret_value = ERROR
        required_fields = ['title', 'link', 'description', 'author', 'pubDate']
        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    if do_print:
                        show(ERROR, f'Missing field in item {i}: {field}')
                    ret_value = ERROR
                elif item[field] == DEFAULT_ITEM_VALUES[field]:
                    if do_print:
                        show(WARNING, f'Default value in item {i}: {field}')
                        print('You might want to customize before publishing')
                    if ret_value != ERROR: ret_value = DEFAULT_PRESENT
    elif basename == ROOT_FILENAME:
        with open(filepath) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                if do_print:
                    show(ERROR, f'Unable to parse the JSON in file {filepath}')
                    print(err)
                ret_value = ERROR
        required_fields = [
                'title',
                'link',
                'description',
                'rootDir',
                'rssFilename'
        ]
        for field in required_fields:
            defaults = DEFAULT_ROOT_VALUES
            if field not in data:
                if do_print:
                    show(ERROR, f'Missing field: {field}')
                ret_value = ERROR
            elif field in defaults and data[field] == defaults[field]:
                if do_print:
                    show(WARNING, f'Default value in field: {field}')
                    print('You might want to customize before publishing')
                if ret_value != ERROR: ret_value = DEFAULT_PRESENT
    else:
        if do_print: show(ERROR, f'Invalid rss filename: {basename}')
        return ERROR
    return ret_value


# __________________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        show_usage_and_exit()

    init()
    action = sys.argv[1]

    if action == 'post':
        filename = sys.argv[2] if len(sys.argv) > 2 else ''
        add_new_post(filename)
    elif action == 'check':
        if len(sys.argv) < 3:
            pass  # TODO Handle the no-filename case.
            exit(0)
        else:
            filename = sys.argv[2]
            check_file(filename)
    elif action == 'root':
        make_root_json_file()
    else:
        show(ERROR, f'Unrecognized action: {action}')

