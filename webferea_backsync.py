#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import sqlite3
from pprint import pprint
from shell import shell

from config_client import client_config



def get_all_changed_webitems(db):
	connection = sqlite3.connect(db)
	connection.row_factory = dict_factory
	cursor = connection.cursor()

	query = '''
		SELECT *
		FROM items
		WHERE webferea <> ''
		'''

	try:
		cursor.execute(query)
		webitems = cursor.fetchall()
		return webitems
	except: 
		return False

def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d


def update_local_items(local_db, webitems):
	
	connection = sqlite3.connect(local_db)
	connection.row_factory = dict_factory
	cursor = connection.cursor()

	for webitem in webitems:

		# get the current local item state
		query = '''SELECT *	FROM items WHERE item_id = "%s" ''' % webitem["item_id"]
		cursor.execute(query)
		localitem = cursor.fetchall()

		# check if something was found
		if not localitem:
			continue

		localitem = localitem[0]

		merge = merge_flags_for_items(webitem, localitem)
		merge["item_id"] = webitem["item_id"]

		query = '''
			UPDATE items 
			SET read = :read,
				marked = :marked
			WHERE item_id = :item_id
			'''
		cursor.execute(query, merge)

	connection.commit()


def merge_flags_for_items(webitem, localitem):
	merge = {}
	merge["read"] = 0
	merge["marked"] = 0

	if webitem["read"] or localitem["read"]:
		merge["read"] = 1

	if webitem["marked"] or localitem["marked"]:
		merge["marked"] = 1

	return merge




def main():
    print("Start Webferea backsync")

    # download from server
    print("download...")
    cmd = "scp -q %s:%s %s" % (client_config["REMOTE_HOST"], \
            client_config["REMOTE_DB_PATH"], client_config["TMP_PATH"] )
    sh = shell(cmd)

    if sh.code is not 0:
        print("failed to download »%s« from host »%s«" % (\
                client_config["REMOTE_DB_PATH"], client_config["REMOTE_HOST"]) )
        exit(1)

    # backsync the flags from the web database
    print("sync...")
    webitems = get_all_changed_webitems(client_config["TMP_PATH"])
    if webitems:
        update_local_items(client_config["LOCAL_DB"], webitems)

    # delete the tmp file again
    #os.remove(client_config["LOCAL_DB"])

    # upload the clients liferea database
    print("upload...")
    cmd = "scp -q %s %s:%s" % (client_config["TMP_PATH"], \
            client_config["REMOTE_HOST"], client_config["REMOTE_DB_PATH"] )
    sh = shell(cmd)

    if sh.code is not 0:
        print("failed to upload »%s« to host »%s«" % (\
                client_config["TMP_PATH"], client_config["REMOTE_HOST"]) )
        exit(1)


if __name__ == "__main__":
    main()

