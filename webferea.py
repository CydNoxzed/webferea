#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import datetime
from math import ceil
from pprint import pprint
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash

from config_server import server_config

# create our little application :)
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE = os.path.join(app.root_path, server_config['DATABASEPATH']),
    DEBUG = server_config['DEBUG'],
    SECRET_KEY = server_config['SECRET_KEY'],
    USERNAME = server_config['USERNAME'],
    PASSWORD = server_config['PASSWORD'],
    ITEMS_PER_PAGE = server_config['ITEMS_PER_PAGE'],
    HOST = server_config['HOST'],
    PORT = server_config['PORT'],
    NODES = server_config['NODES']
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


################################################################################
## MODEL

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = dict_factory
    return rv

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def dict_factory(cursor, row):
    #http://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

#----------------------------------
# Items

def getItem(id):
    db = get_db()
    params = {
        "id": id,
    }
    cur = db.execute('''
        SELECT 
            items.*, 
            node.title AS node_title
        FROM items 
        JOIN node
            ON items.node_id = node.node_id
        WHERE item_id = :id
        ''', params)
    entries = cur.fetchall()
    return entries[0]

def getItemsByNodeNames(node_titles):
    db = get_db()

    hide_read_snipplet = "OR (webferea <> '')" if session["show_read"] else ""

    query = """
        SELECT 
            items.*, 
            node.title AS node_title 
        FROM items 
        JOIN node 
            ON node.node_id = items.node_id
        WHERE 
            node.title IN ('%s')
            AND items.comment = 0 
            AND (( 
                    items.read = 0 
                    AND items.marked = 0 
                ) %s )
            ORDER BY items.date DESC
        """ % ("', '".join(node_titles), hide_read_snipplet)

    cur = db.execute(query)
    entries = cur.fetchall()
    return entries


def getStatistics(node_titles):
    """ Returns the numbers of all items and all read items """
    db = get_db()

    snipplet = ["OR (webferea <> '')", ""]
    counts = []

    for i in snipplet:
        query = """
            SELECT 
                count(node.title) AS count
            FROM items 
            JOIN node 
                ON node.node_id = items.node_id
            WHERE 
                node.title IN ('%s')
                AND items.comment = 0 
                AND (( 
                        items.read = 0 
                        AND items.marked = 0 
                    ) %s )
                ORDER BY items.date DESC
            """ % ("', '".join(node_titles), i)

        cur = db.execute(query)
        entries = cur.fetchall()
        counts.append(entries[0]["count"])

    return counts


#----------------------------------
# Webferea Column

def isWebfereaColumn():
    """ Check if column 'webferea' exists in the table items """
    db = get_db()
    query = """PRAGMA table_info(items)""" 
    cur = db.execute(query)
    entries = cur.fetchall()
    for i in entries:
        if i["name"] == "webferea":
            return True;
    return False

def addWebfereaColumn():
    ''' Add the column 'webferea' to the table items '''
    db = get_db()
    query = '''ALTER TABLE items ADD COLUMN webferea DATETIME;'''
    db.execute(query)
    db.commit()


#----------------------------------
# Item Flags

def setItemFlags(item_id, action):
    ''' Sets the flag of the given item_id by the action '''

    db = get_db()
    update = ""

    if action == "read":
        update = "read = 1"

    elif action == "unread":
        update = "read = 0"

    elif action == "mark":
        update = "marked = 1"

    elif action == "unmark":
        update = "marked = 0"

    # Return false if the action was invalid
    if update is "":
        return False

    query = '''
        UPDATE items 
        SET {},
        webferea = DATETIME('now')
        WHERE item_id = "{}"
        '''.format(update, item_id)
    db.execute(query)
    db.commit()
    return True



################################################################################
## CONTROLLER




#----------------------------------
# Routing

@app.route('/', defaults={'page': 1})
@app.route('/page/<int:page>')
def show_entries(page):

    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not webfereaStart():
        abort(404) 

    # Set the page to 1 if the show_read session was changed
    resetPage = doListActions()
    page = 1 if resetPage else page

    node_filter = app.config['NODES']
    items_per_page = app.config['ITEMS_PER_PAGE']
    infobar = getStatisticString( node_filter )

    # pagination
    entries = getItemsByNodeNames(node_filter)
    p = pagination(page, items_per_page, len(entries))
    entries = itemsFromPaginator(entries, page, items_per_page)

    if not entries and page != 1:
        abort(404)

    # save the current page in the session
    session["page"] = page

    return render_template('list.html', entries=entries, pagination=p, infobar=infobar)


@app.route('/item/<int:item_id>')
def show_item(item_id):

    if not session.get('logged_in'):
        return redirect(url_for('login'))
    webfereaStart()

    entries = getItem(item_id)
    if len(entries) == 0:
        return redirect(url_for('show_entries'))

    doItemActions(item_id)
    entry = getItem(item_id)

    return render_template('item.html', entry=entry)



#----------------------------------
# Functions




def webfereaStart():
    # check if the liferea.db exists and is valid
    if not isSQLite3(app.config['DATABASE']):
        print("No valid sqlite3 file under %s found!" % app.config['DATABASE'])
        return False

    # create the column "webferea" in the table items if its not already there
    if not isWebfereaColumn():
        addWebfereaColumn()

    # create default show_read session key
    if "show_read" not in session:
        session["show_read"] = True

    return True




def doListActions():
    ''' Perform the actions on the list '''
    req = request.args.get('action', '')
    ret = False
    msg = ""
    if req == "show_read":
        session["show_read"] = True
        msg = "Show read items"
        ret = True
    elif req == "hide_read":
        session["show_read"] = False
        msg = "Hide read items"
        ret = True

    if len(msg)>0:
        flash(msg)
    return ret


def doItemActions(item_id):
    ''' Perform the actions on the given item_id '''
    req = request.args.get('action', '')

    if not req:
        return

    if req == "read":
        ret = setItemFlags(item_id, req)
        msg = "Set read flag" if ret else "Cant set read flag"
    elif req == "unread":
        ret = setItemFlags(item_id, req)
        msg = "Unset read flag" if ret else "Cant unset read flag"
    elif req == "mark":
        ret = setItemFlags(item_id, req)
        msg = "Set marked flag" if ret else "Cant set marked flag"
    elif req == "unmark":
        ret = setItemFlags(item_id, req)
        msg = "Unset marked flag" if ret else "Cant unset marked flag"

    if len(msg)>0:
        flash(msg)



def isSQLite3(filename):
    """
    Check if the sqlite3file is valid
    credits to: http://stackoverflow.com/questions/12932607/
    """
    if not os.path.isfile(filename):
        return False
    if os.path.getsize(filename) < 100: # SQLite database file header is 100 bytes
        return False
    else:
        fd = open(filename, 'rb')
        Header = fd.read(100)
        fd.close()

        if Header[0:16] == b'SQLite format 3\000':
            return True
        else:
            return False


def getStatisticString(node_filter):
    statistics = getStatistics(node_filter)
    dbtimestamp = os.path.getmtime(app.config['DATABASE'])
    dbtimestr = datetime.datetime.fromtimestamp( int(dbtimestamp) \
                    ).strftime('%Y-%m-%d %H:%M:%S')
    return "%s unread items of %s left | last sync %s" % (statistics[1], statistics[0], dbtimestr)


#----------------------------------
# Pageination


def itemsFromPaginator(items, page, items_per_page):
    first = (page * items_per_page) - items_per_page
    last = first + items_per_page
    return items[first:last]


def pagination(page, per_page, total_count):
    paginator = {}
    paginator["has_prev"] = bool(page > 1)
    paginator["has_next"] = bool(page < (total_count / per_page) )
    paginator["page"] = page
    return paginator



####################################
# Login-stuff


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))



################################################################################
## VIEWER

@app.template_filter('datetime')
def format_datetime(timestamp):
    format = '%Y-%m-%d %H:%M:%S'
    return datetime.datetime.fromtimestamp( timestamp ).strftime(format)


################################################################################


if __name__ == "__main__":
    app.run( host=app.config['HOST'], port=app.config['PORT'] )
