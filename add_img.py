#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    add_img.py

    Usage:

        add_img.py rss_items.json

    This will wrap the `description` property in a CDATA block, and add an empty
    img tag as well. This is meant to help add images to posts.
"""


# __________________________________________________________________________
# Imports

import json
import sys


# __________________________________________________________________________
# Imports

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print(__doc__)
        exit(0)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    for item in data:
        desc = item['description']
        if 'CDATA' not in desc:
            item['description'] = f'<![CDATA[{desc} <img src="IMG_SRC">]]>'

    with open(sys.argv[1], 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)

