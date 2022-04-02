#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    rss.py

    A simple tool to create and maintain rss feed files.
    This is an RSS *writer*, not a reader.

    Usage:

        # When you have a new post, cd into the directory of that post and run
        # this, then edit the fields in the rss_items.json file:

        rss.py post [filename_of_post_html_file] [-7 7date_str]


        # Run this command to designate the local root directory of your
        # website. This creates a template rss_root.json file for you to edit,
        # and this root directory is used to infer what the url paths will be to
        # posts in subdirectories:

        rss.py root


        # Run this command to generate the current rss feed file; this uses the
        # values of rss_root.json (which may be in a parent dir), and all
        # descendant rss_items.json files:

        rss.py make


        # Run this command to verify that rss_{root,items}.json files are
        # correctly formatted. If you run this in the root directory without any
        # parameters, it checks the validity of all rss_{root,items}.json files
        # recursively:

        rss.py check [json_filename]

    You can set a default author name in the root json file by providing a value
    for the field name "defaultAuthor". If you set this, then new posts will
    automatically have that author assigned to them.

"""


# __________________________________________________________________________
# Imports

import copy
import json
import os
import subprocess
import sys
# Uncomment the line below to enable use of the xml library.
# import xml.etree.ElementTree as ET

from datetime import datetime
from datetime import timedelta
from email    import utils
from pathlib  import Path


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


# __________________________________________________________________________
# Functions that use the xml library

# I'm leaving these here in case I one day want to actually use the xml library.
# However, in the meantime, I found that the short alternative below - a total
# of 36 lines of non-blank/non-comment body code, works as a full replacement.
# (The xml-using version is 12 lines, so I'd say that I was able to replace my
#  use case of the xml library with 24 lines of code.)

if False:

    def make_new_xml_tree(root_tag):
        root_elt = ET.Element(root_tag)
        tree = ET.ElementTree(root_elt)
        return tree, root_elt

    def add_elt(parent, tag, text=None):
        elt = ET.SubElement(parent, tag)
        if text:
            elt.text = text
        return elt

    def append_item(parent, item_dict):
        item_elt = add_elt(parent, 'item')
        for key, value in item_dict.items():
            add_elt(item_elt, key, value)

    def write_xml(tree, file):
        ET.indent(tree)
        tree.write(file, encoding='utf-8', xml_declaration=True)


# __________________________________________________________________________
# Functions that replace the xml library

# These functions internally use a json-encoded rss object to temporarily store
# a tree as it's being built. The format is: there is a dict as the base object.
# Each dict has at least the key "tag" (with the tag name as value).
# It may also have the key "subtags" with a list of subtags, and potentially
# "text" with a string as the text.
# It's true that this format cannot handle all xml trees, but it suffices for
# this use case.

# This returns `tree, root_elt`. Use `tree` to print out the xml.
# Use root_elt as a parent to add things to the tree.
def make_new_xml_tree(root_tag, attribs=None):
    tree     = {'tag': root_tag, 'value': []}
    root_elt = tree['value']
    if attribs:
        tree['attribs'] = attribs
    return tree, root_elt

# The `parent` is expected to be a Python list.
def add_elt(parent, tag, text=None, attribs=None):
    obj = {'tag': tag, 'value': []}
    if text:
        obj['text'] = text
    if attribs:
        obj['attribs'] = attribs
    parent.append(obj)
    return obj['value']

def append_item(parent, item_dict):
    item_elt = add_elt(parent, 'item')
    for key, value in item_dict.items():
        add_elt(item_elt, key, value)

def write_xml(xml_as_json, file, prefix=None):
    do_need_post_indent = False
    do_i_own_f = type(file) is str
    f = file if not do_i_own_f else open(file, 'w')
    if prefix is None:  # This is the root call.
        f.write("<?xml version='1.0' encoding='utf-8'?>\n")
        prefix = ''
    if type(xml_as_json) is dict:
        tag = xml_as_json['tag']
        tag_str = f'<{tag}>'
        if 'attribs' in xml_as_json:
            attrib_items = xml_as_json['attribs'].items()
            attrib_str = ' '.join([f'{k}="{v}"' for k, v in attrib_items])
            tag_str = f'<{tag} {attrib_str}>'
        f.write(prefix + tag_str)
        value_key = 'text' if 'text' in xml_as_json else 'value'
        do_indent = write_xml(xml_as_json[value_key], f, prefix)
        if do_indent:
            f.write(prefix)
        f.write(f'</{tag}>\n')
    elif type(xml_as_json) is str:
        f.write(xml_as_json)
    elif type(xml_as_json) is list:
        if len(xml_as_json) > 0:
            f.write('\n')
            do_need_post_indent = True
        for item in xml_as_json:
            write_xml(item, f, prefix + '  ')
    if do_i_own_f:
        f.close()
    return do_need_post_indent


# __________________________________________________________________________
# Functions to support 7date notation

# This expects n and b to be integers with n >= 0 and b > 1.
# This returns the number n written in base b, as a string.
def tobase(n, b):
    assert n >= 0 and b > 1
    digits = []
    while n > 0:
        digits.append(n % b)
        n //= b
    digits = digits if digits else [0]
    return ''.join(map(str, reversed(digits)))

# This converts string s, which is expected to have digits 0 through (b-1),
# into a Python number, which is returned.
# This assumes 1 < b <= 10, and that s represents a nonnegative integer.
def frombase(s, b):
    assert 1 < b <= 10
    n = 0
    for char in s:
        n *= b
        d = ord(char) - ord('0')
        if not 0 <= d < b:
            raise ValueError(f'Invalid digit in base-{b} number "{s}"')
        n += d
    return n

# This expects a valid 7date string (either standard or digital format); it
# returns a datetime object for the beginning of the given day.
# If there is a parsing error, this throws a ValueError.
def to_datetime(sevendate_str):
    sevendate_str = sevendate_str.strip()  # Ignore surrounding whitespace.
    dot = sevendate_str.find('.')
    if dot == -1:
        # Assume it's in digital format, which is YYYY-DDDD.
        year_str = sevendate_str[0:4]
        day_str  = sevendate_str[5:]
    else:
        # Assume it's in standard format, which is D+.YYYY.
        day_str  = sevendate_str[:dot]
        year_str = sevendate_str[dot + 1:]
    day_num  = frombase(day_str, 7)
    year_num = int(year_str)
    time = datetime(year_num, 1, 1) + timedelta(days=day_num)
    return time

# This expects either None or a datetime string. If you pass in None (or no
# arguments), it provides the 7date string.
def to_string(time=None, do_use_digital_format=False):
    if time is None:
        time = datetime.now()
    year = str(time.year)
    day  = tobase(time.timetuple().tm_yday - 1, 7)
    if do_use_digital_format:
        # The format specifier "0>4s" means "right-align (>) the string (s) in
        # `day`, and pad with '0' chars to achieve minimum length 4."
        # https://peps.python.org/pep-3101/#standard-format-specifiers
        return f'{year}-{day:0>4s}'
    else:
        return f'{day}.{year}'


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

def show_usage_and_exit():
    exec_name = os.path.basename(sys.argv[0])
    print(__doc__.replace('rss.py', exec_name))
    exit(0)

# In the future, this may take an optional argument with some indication of
# the timestamp for which we provide a date string.
def get_date_str(time=None):
    time = time if time else datetime.now()
    return utils.format_datetime(time.astimezone())

def make_new_post_obj(sevendate_str=None):
    obj = copy.copy(DEFAULT_ITEM_VALUES)
    time = to_datetime(sevendate_str) if sevendate_str else None
    obj['pubDate'] = get_date_str(time)
    return obj

# On success, this returns a Path object pointing to the root json file.
# If the file can't be found, this returns ERROR.
# This doesn't print anything in either case.
def find_root_json_filepath():
    curr_dir = Path.cwd()
    while True:
        root_json_filepath = curr_dir / ROOT_FILENAME
        if root_json_filepath.exists():
            return root_json_filepath
        if curr_dir.parent == curr_dir:
            return ERROR
        curr_dir = curr_dir.parent

# If successful, return root_path, root_data, where root_path is the path to the
# publication root as specified in the root rss file, and root_data is the json
# data as ready directly from the root rss file. If not successful (such as if
# the root file could not be found), then return ERROR, ERROR.
def find_root_data():
    root_json_filepath = find_root_json_filepath()
    if root_json_filepath == ERROR:
        return ERROR, ERROR
    with open(root_json_filepath) as f:
        root_data = json.load(f)
    root_path = root_json_filepath.parent / root_data['rootDir']
    return root_path, root_data

# Try to infer the path of the URL for the current directory. This succeeds if
# we can locate an rss_root.json file in this directory or a parent directory,
# in which case that root file is used to determine the publication root dir. In
# case we can't find the root, then this returns the empty string.
def guess_path(filename=None):
    root_path, root_data = find_root_data()
    if root_path == ERROR:
        return filename
    basepath = Path.cwd() if not filename else Path.cwd() / filename
    rel_path_str = str(basepath.relative_to(root_path))
    if rel_path_str == '.':
        rel_path_str = ''
    return 'http://' + rel_path_str

def add_new_post(filename='', sevendate_str=None):
    data = []
    if os.path.exists(ITEMS_FILENAME):
        error_msgs = check_file(ITEMS_FILENAME, do_print=False)
        if len(error_msgs) > 0:
            msg = f'Please fix the issues below first in {ITEMS_FILENAME}:'
            show(ERROR, msg)
            for error_msg in error_msgs:
                print(' * ' + error_msg)
            print("Note: I don't support new posts if an existing post has " +
                  "default values for any fields.")
        else:
            with open(ITEMS_FILENAME) as f:
                data = json.load(f)
    obj = make_new_post_obj(sevendate_str)
    guessed_path = guess_path(filename)
    _, root_data = find_root_data()
    if root_data and 'defaultAuthor' in root_data:
        obj['author'] = root_data['defaultAuthor']
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

# If there is no 7date string, this returns None; otherwise it returns the 7date
# string.
def check_for_sevendate_str(argv):
    for i in range(len(argv) - 1):
        if argv[i] == '-7':
            return argv[i + 1]
    return None

# If do_dry_run is True, this returns a list of all error messages found.
# This will be an empty list if everything appears to be in order.
def make_rss_file(do_dry_run=False):

    error_msgs = []

    do_print = not do_dry_run
    root_json_filepath = find_root_json_filepath()
    if root_json_filepath == ERROR:
        error_msg = 'Could not file root file here or in any parent dir'
        if not do_dry_run:
            show(ERROR, error_msg)
            exit(1)
        return [error_msg]

    error_msgs = check_file(root_json_filepath, do_print)
    if error_msgs:
        if do_dry_run:
            error_msgs = [f'(In root json file) {msg}' for msg in error_msgs]
        else:
            print(f'^^ The above message is for {root_json_filepath}.\n')
            exit(1)
    root_path, root_data = find_root_data()

    # Start to build the xml object we'll write out.
    tree, rss_root = make_new_xml_tree('rss', {'version': '2.0'})
    channel = add_elt(rss_root, 'channel')
    for field in ['title', 'link', 'description']:
        add_elt(channel, field, root_data[field])

    # Walk directories from the root, finding all item json files.
    cwd = Path.cwd()
    all_items = []
    for root, dirs, files in os.walk(str(root_path)):
        if ITEMS_FILENAME in files:
            filepath = str(Path(root) / ITEMS_FILENAME)
            check_errs = check_file(filepath, do_print)
            try:
                rel_path = str((Path(root) / ITEMS_FILENAME).relative_to(cwd))
            except ValueError:
                rel_path = filepath
            if check_errs:
                if do_dry_run:
                    error_msgs += [f'({rel_path}) {msg}' for msg in check_errs]
                else:
                    print(f'^^ The above message is for {filepath}.\n')
                    exit(1)
            with open(filepath) as f:
                items_data = json.load(f)
            all_items += items_data

    if do_dry_run:
        return error_msgs

    # Sort items by date.
    all_items = sorted(
            all_items,
            key = lambda item: utils.parsedate_to_datetime(item['pubDate']),
            reverse = True
    )

    # Determine the channel's overall pubDate and lastBuildDate (which is now).
    if all_items:
        add_elt(channel, 'pubDate', all_items[0]['pubDate'])
    now = datetime.now()
    add_elt(channel, 'lastBuildDate', utils.format_datetime(now.astimezone()))

    # Include the most-recent 10 items.
    for item in all_items[:10]:
        append_item(channel, item)

    # Format and write out the xml to disk.
    rss_filepath = str(root_path / root_data['rssFilename'])
    write_xml(tree, rss_filepath)

    print(f'Success: Wrote RSS feed to the file {rss_filepath}')

# This returns a list of error messages; the list is empty if everything is ok.
# If do_print is False, this prints nothing. Otherwise, this prints only errors
# and warnings.
def check_file(filepath, do_print=True):
    error_msgs = []

    def handle_error(error_msg, is_warning=False):
        level = WARNING if is_warning else ERROR
        if do_print:
            show(level, error_msg)
        error_msgs.append(error_msg)

    basename = os.path.basename(filepath)
    if basename == ITEMS_FILENAME:
        with open(filepath) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                handle_error(f'Unable to parse the JSON in file {filepath}' +
                              '\n' + str(err))
                return error_msgs
        required_fields = ['title', 'link', 'description', 'author', 'pubDate']
        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    handle_error(f'Missing field in item {i}: {field}')
                elif item[field] == DEFAULT_ITEM_VALUES[field]:
                    handle_error(
                            f'Default value in item {i} for {field}',
                            is_warning=True
                    )
    elif basename == ROOT_FILENAME:
        with open(filepath) as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as err:
                handle_error(f'Unable to parse the JSON in file {filepath}' +
                              '\n' + str(err))
                return error_msgs
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
                handle_error(f'Missing field: {field}')
            elif field in defaults and data[field] == defaults[field]:
                handle_error(
                        f'Default value found for {field}',
                        is_warning=True
                )
    else:
        handle_error(f'Invalid rss filename: {basename}')

    return error_msgs


# __________________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        show_usage_and_exit()

    init()
    action = sys.argv[1]

    if action == 'post':
        filename = sys.argv[2] if len(sys.argv) > 2 else ''
        sevendate_str = check_for_sevendate_str(sys.argv)
        add_new_post(filename, sevendate_str)
    elif action == 'check':
        if len(sys.argv) < 3:
            error_msgs = make_rss_file(do_dry_run=True)
            if error_msgs:
                print('The following issues were found:')
                for error_msg in error_msgs:
                    print(' * ' + error_msg)
            else:
                root_json_filepath = find_root_json_filepath()
                print(f'The root json file is {root_json_filepath}')
                print('Ship shape! (no errors found)')
        else:
            filename = sys.argv[2]
            error_msgs = check_file(filename)
            if not error_msgs:
                print('Jolly good! (no errors)')
    elif action == 'root':
        make_root_json_file()
    elif action == 'make':
        make_rss_file()
    else:
        show(ERROR, f'Unrecognized action: {action}')

