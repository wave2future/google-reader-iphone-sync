#!/usr/bin/env python
# general includes
import sys, glob, urllib2

# local includes
import config
from db import DB
from item import Item
from misc import *
from output import *
from lib.GoogleReader import GoogleReader, CONST
import app_globals
import template


def reader_login():
	"""
	Login to google-reader with credentials in OPTIONS.
	Stores the logged-in reader in the global READER variable
	Raises exception if authentication fails
	"""
	if app_globals.OPTIONS['test']:
		info("using a mock google reader...")
		return

	app_globals.READER = GoogleReader()
	app_globals.READER.identify(
		app_globals.OPTIONS['user'],
		app_globals.OPTIONS['password'])
	
	if not app_globals.READER.login():
		raise Exception("Login failed")



def execute():
	"""
	Logs in, syncs and downloads new items
	"""
	ensure_dir_exists(app_globals.OPTIONS['output_path'])
	ensure_dir_exists(app_globals.OPTIONS['output_path'] + '/' + app_globals.CONFIG['resources_path'])

	reader_login()

	line()
	app_globals.DATABASE = DB()
	app_globals.DATABASE.sync_to_google()
	app_globals.DATABASE.cleanup() # remove old _resources files
	
	update_templates()

	if app_globals.OPTIONS['no_download']:
		info("not downloading any new items...")
	else:
		download_new_items()
	app_globals.DATABASE.close()

def update_templates():
	files = [None, None, None]
	files_to_edit = glob.glob(app_globals.OPTIONS['output_path'] + '/*.html')
	files_to_edit.append(None)
	for f in files_to_edit:
		
		files.pop(0)
		files.append(f)
		
		obj = {}
		prev = files[-3]
		next = files[-1]
		filename = files[-2]
		if prev is not None:
			obj['nav_prev'] = '<a href="' + urllib2.quote(slashify_dbl_quotes(os.path.basename(prev))) + '" class="prev">PREVIOUS</a>'
		if next is not None:
			obj['nav_next'] = '<a href="' + urllib2.quote(slashify_dbl_quotes(os.path.basename(next))) + '" class="next">NEXT</a>'
		if filename is not None:
			obj['nav_up'] = '<a href="./" class="up">UP</a>'
			debug("Updating template for file: " + filename)
			template.update_template('template/item.html', filename)

def download_new_items():
	"""
	Downloads new items from google reader
	"""
	for feed_tag in app_globals.OPTIONS['tag_list']:
		puts("Fetching maximum %s items from feed %s" % (app_globals.OPTIONS['num_items'], feed_tag))
		feed = app_globals.READER.get_feed(None,
			CONST.ATOM_PREFIXE_LABEL + feed_tag,
			count = app_globals.OPTIONS['num_items'],
			exclude_target = CONST.ATOM_STATE_READ,	# get only unread items
			order = CONST.ORDER_REVERSE)			# oldest first
	
		for entry in feed.get_entries():
			debug(" -- %s -- " % app_globals.STATS['items'])
			app_globals.STATS['items'] += 1
		
			if entry is None:
				app_globals.STATS['failed'] += 1
				puts(" ** FAILED **")
				continue
		
			debug_verbose(entry.__repr__())
		
			item = Item(entry, feed_tag)
			state = app_globals.DATABASE.is_read(item.google_id)
			name = item.basename
		
			if state is None:
				if not item.is_read:
					try:
						puts("NEW: " + item.title)
						danger("About to output item")
						item.process()
						item.save()
						app_globals.STATS['new'] += 1
					except Exception,e:
						puts(" ** FAILED **: " + str(e))
						if in_debug_mode():
							raise
						app_globals.STATS['failed'] += 1
			else:
				if state == True or item.is_read:
					# item has been read either online or offline
					pus("READ: " + name)
					app_globals.STATS['read'] += 1
					danger("About to delete item")
					item.delete()
		
		line()
	
	info("%s NEW items" % app_globals.STATS['new'])
	info("%s items marked as read" % app_globals.STATS['read'])
	if app_globals.STATS['failed'] > 0:
		puts("%s items failed to parse" % app_globals.STATS['failed'])


def main():
	"""
	Main program entry point - loads config, parses otions and kicks off the sync process
	"""
	config.bootstrap()
	config.load()
	config.parse_options()
	config.check()
	
	if not app_globals.OPTIONS['template_only']:
		execute()
	else:
		info("Updating templates for all existing items...")
		update_templates()
	puts("Sync complete.")


if __name__ == '__main__':
	sys.exit(main())
