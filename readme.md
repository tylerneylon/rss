# rss.py

*A simple tool to create and maintain rss feed files; an rss writer.*

This tool is meant to be used by folks who like bare-bones tools that do just
what is needed. I've designed it to create an RSS feed for my homepage.

## Installing

    git clone https://github.com/tylerneylon/rss.git
    sudo ln -s $(cd rss; pwd)/rss.py /usr/local/bin/rss

After this, you should be able to use the tool via the command `rss`.
This assumes that `/usr/local/bin` is in your path; it typically is.

## How rss.py works

This tool is designed to work with a local static copy of your website. It's
fine if you also have dynamic content (urls that are not reflected by static
files). In general, you will create small json files that track the key fields
of your rss feed for you. Each time you add a new post, you will add some
corresponding json data to disk with the help of rss.py. Then you recompile your
feed file and push that into production.

After installing this tool (assuming you execute the `ln` command above), you
can initiate a new local directory by running `rss root`. This will create a
file called `rss_root.json` in the current directory, which ought to be at or
above the top of the directory tree for your site. (I keep mine above the tree
so that I can push the full tree and my `rss_root.json` file is not part of my
site.) Once you create this file, you may want to edit the file to set your own
personal website title, link, description, `rootDir` (the directory that
represents the root of your site), and `rssFilename` (the file name you choose
for your rss feed). You may optionall set a `defaultAuthor` value if you
typically have a single author of your posts.

After that, each time you add a new post, cd into the directory of the post and
run, for example `rss post my_post_name.html`. This will create a new entry in
the local `rss_items.json` file. You edit that file to set the title and
description of your post (and possibly the author or date if you'd like to
customize those). `rss.py` won't allow you to compile a feed file if you leave
any default values in your json files, so you must fill out those values.

Whenever you're ready to push an updated feed file, run `rss make` and that push
the resulting file into production.

You will probably also want to include a `link` element like this in the `head`
of your landing page:

    <link data-rh="true" rel="alternate" type="application/rss+xml"
     title="RSS" href="https://YOURDOMAIN.com/feed"/>

## Help string

Here's a shorter version of the above description:


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
