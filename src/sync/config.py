"""
Exports:
CONFIG
OPTIONS
parse_options()
load_config()
"""
from getopt import getopt
import sys
import re
import lib
import logging
import logging.config
import ConfigParser

# local imports
from misc import *
from output import *
import app_globals


required_keys = ['user','password']

bootstrap_options = ('c:so', ['config=','show-status','output-path=', 'logging=','logdir=','loglevel='])
main_options = ("n:Co:dth", [
		'num-items=',
		'cautious',
		'aggressive',
		'no-download',
		'test',
		'help',
		'user=',
		'password=',
		'tag=',
		'tag-list-only',
		'newest-first',
		'report-pid',
		])
all_options = (bootstrap_options[0] + main_options[0],
               bootstrap_options[1] + main_options[1])

def unicode_argv(args = None):
	if args is None:
		args = sys.argv[1:]
	return [unicode(arg, 'utf-8') for arg in args]

def bootstrap(argv = None):
	argv = unicode_argv(argv)
	(opts, argv) = getopt(argv, *all_options)
	for (key,val) in opts:
		if key == '--config' or key == '-c':
			set_opt('user_config_file', val)
		elif key == '--show-status' or key == '-s':
			set_opt('show_status', True)
		elif key == '-o' or key == '--output-path':
			set_opt('output_path', val)
		elif key == '--logging':
			set_opt('logging', val)
		elif key == '--logdir':
			set_opt('logdir', val)
		elif key == '--loglevel':
			set_opt('loglevel', val)


def defaults(*args):
	return tuple(["(default: %s)" % app_globals.OPTIONS[pythonise_option_key(key)] for key in args])

def parse_options(argv = None):
	"""
Usage:
  -n, --num-items=[val]  set the number of items to download (per feed)
  -c, --config=[file]    load config from file (must be in yaml format)
  -d, --no-download      don't download new items, just tell google reader about read items
  -t, --test             run in test mode (don't notify google reader of anything)
  -c, --cautious         cautious mode - prompt before performing destructive actions
  -o, --output-path=[p]  set the base output path (where items and resources are saved)
  --tag-list-only        just get the current list of tags and exit
  --newest-first         get newest items first instead of oldest
  --user=[username]      set the username
  --password=[pass]      set password
  --tag=[tag_name]       add a tag to the list of tags to be downloaded. Can be used multiple times
  --report-pid           report any existing sync PID
  --aggressive           KILL any other running sync process
                         (the default is to fail to start if another sync process is running)
  --logdir=[log_dir]     logging base directory
  --logging=[log_conf]   override log configuration file
  --loglevel=[log_conf]  set the console output log level
"""
	tag_list = []
	argv = unicode_argv(argv)

	(opts, argv) = getopt(argv, *all_options)
	for (key,val) in opts:
		if key in ['-c','--config','-s','--show-status', '--logging', '--logdir', '--loglevel']:
			# already processed
			pass
		
		elif key == '-C' or key == '--cautious':
			set_opt('cautious', True)
			info("Cautious mode enabled...")
		elif key == '-n' or key == '--num-items':
			set_opt('num_items', int(val))
			info("Number of items set to %s" % app_globals.OPTIONS['num_items'])
		elif key == '-d' or key == '--no-download':
			set_opt('no_download', True)
			info("Downloading turned off..")
		elif key == '-t' or key == '--test':
			set_opt('test', True)
		elif key == '-h' or key == '--help':
			print parse_options.__doc__
			sys.exit(1)
		elif key == '--password':
			set_opt('password',val, disguise = True);
		elif key == '--tag':
			tag_list.append(val)
			set_opt('tag_list', tag_list)

		else:
			if key.startswith('--') and key[2:] in main_options[1]:
				# it's a flag
				val = True
			success = set_opt(key, val)
			if not success:
				print "unknown option: %s" % (key,)
				print parse_options.__doc__ 
				sys.exit(1)

	if len(argv) > 0:
		set_opt('num_items', int(argv[0]))
		info("Number of items set to %s" % app_globals.OPTIONS['num_items'])

	

def pythonise_option_key(key):
	"""
	Convert `CamelCase` and `option-style` keys into `python_style` keys
		>>> pythonise_option_key('Capital')
		'capital'
		>>> pythonise_option_key('CamelCase')
		'camel_case'
		>>> pythonise_option_key('Camel_Case')
		'camel_case'
		>>> pythonise_option_key('option-Style')
		'option_style'
		>>> pythonise_option_key('option-style')
		'option_style'
	"""
	key = re.sub('([a-z0-9])([A-Z])', '\\1_\\2', key)
	key = key.replace('-', '_')
	key = key.replace('__', '_')
	key = key.lower()
	return key

path_keys = ['output_path','user_config_file']
def set_opt(key, val, disguise = False):
	if key.startswith('--'):
		key = key[2:]
	key = pythonise_option_key(key)
	if "pass" in key or "Pass" in key:
		disguise = True
	if key in path_keys:
		val = os.path.expanduser(val)
	debug("set option %s = %s" % (key, val if disguise is False else "*****"))
	if key not in app_globals.OPTIONS:
		debug("Ignoring key: %s" % (key,))
		return False
	app_globals.OPTIONS[key] = val
	return True

def init_logging():
	logdir = app_globals.OPTIONS['logdir']
	ensure_dir_exists(logdir)
	env = {
		'logdir':logdir,
		'loglevel': app_globals.OPTIONS['loglevel'].upper(),
	}
	try:
		logging.config.fileConfig(app_globals.OPTIONS['logging'], env)
	except ConfigParser.Error:
		print "ERROR: logging setup FAILED with file: %s, env: %r" % (app_globals.OPTIONS['logging'],env)
		raise

def load(filename = None):
	"""
	Loads config.yml (or OPTIONS['user_config_file']) and merges it with the global OPTIONS hash
	"""
	if filename is None:
		filename = app_globals.OPTIONS['user_config_file']
		if not (os.path.isfile(filename) or os.path.isabs(filename)):
			filename = os.path.join(app_globals.OPTIONS['output_path'], filename)

	debug("Loading configuration from %s" % filename)
	
	try:
		extension = filename.split('.')[-1].lower()
		if extension == 'yml':
			config_hash = load_yaml(filename)
		elif extension == 'plist':
			config_hash = load_plist(filename)
		else:
			warning("unknown filetype: %s" % (extension,))
			config_hash = {}

		if config_hash is not None:
			for key,val in config_hash.items():
				set_opt(key, val)

	except IOError, e:
		warning("Can't load %s: %s" % (filename,e))

def load_yaml(filename):
	try:
		import yaml
		return do_with_file(filename, 'r', yaml.load)
	except ImportError, e:
		warning("YAML library failed to load: %s" % (e, ))

def load_plist(filename):
	import plistlib
	return do_with_file(filename, 'r', plistlib.readPlist)


def check():
	for k in required_keys:
		if not k in app_globals.OPTIONS or app_globals.OPTIONS[k] is app_globals.PLACEHOLDER:
			raise RuntimeError("Required setting \"%s\" is not set." % (k,))

if __name__ == '__main__':
	import doctest
	doctest.testmod()
