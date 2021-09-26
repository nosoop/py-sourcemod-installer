#!/usr/bin/python3

"""
SourceMod installer / updater script with cross-platform support and no external Python
dependencies.

This requires Python 3.8+, as it uses the dirs_exist_ok kwarg in shutil.copytree() and
f-strings.
"""

import urllib.request
import tempfile
import shutil
import os
import pathlib
import contextlib
import sys
import functools

LICENSE_PROMPT = """\
SourceMod is licensed under GPLv3.  For more information, see https://www.sourcemod.net/license.php
You must acknolwedge and comply with the license agreement to install and use SourceMod.
Proceed with installation?"""

@contextlib.contextmanager
def deferred_file_remove(file, *args, **kwargs):
	""" Opens a file for access, deleting it once the context is closed. """
	f = open(file, *args, **kwargs)
	try:
		yield f
	finally:
		f.close()
		os.remove(file)

@functools.lru_cache()
def get_version_from_branch(branch):
	"""
	A really dumb scraping mechanism to identify the version associated with a branch.
	Valid branches include 'stable' and 'dev' (alias of 'master').
	
	I'd prefer to not have to use this, but SourceMod hasn't implemented the functionality in
	their redirect script.
	"""
	import urllib.request
	import html.parser
	
	class LinkExtractor(html.parser.HTMLParser):
		def __init__(self):
			super(LinkExtractor, self).__init__()
			self.refs = set()
		
		def handle_starttag(self, tag, attrs):
			if tag != 'a':
				return
			for name, value in attrs:
				if name == 'href':
					self.refs.add(value)
	
	parser = LinkExtractor()
	r = urllib.request.Request(
		url = f'https://www.sourcemod.net/downloads.php?branch={branch}',
		headers = { "User-Agent": "SourceMod Update Utility" }
	)
	with urllib.request.urlopen(r) as data:
		page = data.read().decode(data.headers.get_content_charset())
		parser.feed(page)
	
	# find some downloadable file and return its directory name
	for ref in filter(lambda l: '.zip' in l, parser.refs):
		path = pathlib.PurePosixPath(ref)
		return path.parent.name
	return None

def confirm(*args, **kwargs):
	"""
	Utility function that prompts the user with a confirmation.
	
	Returns True / False if the user provided any input, None if not an interactive terminal or
	if the input is invalid.
	
	Contains a 'default' kwarg that can be set to True to allow by default.
	"""
	import distutils.util
	import itertools
	
	if sys.stdin.isatty() and sys.stdout.isatty():
		confirmation = '[Y/n]' if kwargs.pop("default", False) else '[y/N]'
		prompt = ' '.join(itertools.chain(args, [ confirmation, '' ]))
		try:
			return distutils.util.strtobool(input(prompt))
		except ValueError:
			pass
	return None

def main():
	import platform
	import argparse
	import pydoc
	
	parser = argparse.ArgumentParser(description = "Installs or upgrades SourceMod.")
	
	parser.add_argument("directory", help = "the server's game directory",
			type = pathlib.Path)
	
	# autodetects platform (assumes this works correctly for windows / linux / mac)
	parser.add_argument("--platform", help = "the server's operating system",
			default = platform.system())
	
	parser.add_argument("--version", help = "the SourceMod version to install",
			default = "1.10")
	parser.add_argument("--branch", help = "the SourceMod branch to install (resolves version)")
	
	parser.add_argument("--url", help = "a URL to a SourceMod package to install "
			"(ignores version / os / branch)")
	
	parser.add_argument("--archive", help = "an existing package to install; "
			"either compressed file or directory "
			"(ignores version / os / branch / url)", type = pathlib.Path)
	
	parser.add_argument("--no-upgrade-plugins", help = "plugins will not be copied from "
			"upgrade package (ignored if first time installing)", action = "store_true")
	
	args = parser.parse_args()
	
	params = {
		'version': args.version,
		'os': args.platform.lower()
	}
	
	if args.branch:
		resolved_version = get_version_from_branch(args.branch)
		if resolved_version:
			params['version'] = resolved_version
			print(f"Resolved branch name {args.branch} to version {resolved_version}")
		else:
			raise ValueError(f"Failed to resolve branch name {args.branch}")
	
	r = urllib.request.Request(
		url = f'https://sourcemod.net/latest.php?{urllib.parse.urlencode(params)}',
		headers = { "User-Agent": "SourceMod Update Utility"}
	)
	
	if args.url:
		r.full_url = args.url
	
	tempname = None
	package = None
	
	if args.archive and args.archive.exists():
		if args.archive.is_file():
			# use local archive
			with tempfile.NamedTemporaryFile(delete = False, suffix = ''.join(args.archive.suffixes)) as local,\
					open(args.archive, mode = 'rb') as remote:
				shutil.copyfileobj(remote, local)
				tempname = local.name
		elif args.archive.is_dir():
			# use unpacked archive
			package = args.archive
	else:
		# download file from internet
		with urllib.request.urlopen(r) as remote:
			pkg = pathlib.Path(urllib.parse.urlsplit(remote.geturl()).path.split('/')[-1])
			print('Downloading SourceMod package', pkg)
			with tempfile.NamedTemporaryFile(delete = False, suffix = ''.join(pkg.suffixes)) as local:
				shutil.copyfileobj(remote, local)
				tempname = local.name
	
	with contextlib.ExitStack() as es:
		if tempname:
			archive_file = es.enter_context(deferred_file_remove(tempname, 'rb'))
			package = es.enter_context(tempfile.TemporaryDirectory())
			shutil.unpack_archive(archive_file.name, package)
		
		if not package:
			print("No archive file specified")
			sys.exit(1)
		
		path_sm = pathlib.Path('addons', 'sourcemod')
		
		if not (args.directory / path_sm).exists():
			# first install, make sure that user acknowledges license
			print("Performing full install of SourceMod.")
			with open(package / path_sm / 'LICENSE.txt', 'rt') as license:
				pydoc.pager(license.read())
			print()
			result = confirm(LICENSE_PROMPT)
			
			if result:
				shutil.copytree(package, args.directory, dirs_exist_ok = True)
				print("Installation complete.");
				sys.exit(0)
			else:
				print("Installation cancelled.")
				sys.exit(1)
		
		# replace the contents of `bin/` and `configs/geoip/`
		for d in { ('bin',), ('configs', 'geoip') }:
			sd = path_sm / pathlib.Path(*d)
			if (args.directory / sd).exists():
				shutil.rmtree(args.directory / sd)
			if (package / sd).exists():
				shutil.copytree(package / sd, args.directory / sd, dirs_exist_ok = False)
		
		# update the contents of `configs/sql-init-scripts/`, `extensions/`, `scripting/`,
		# `translations` without touching other existing files
		for d in { ('configs', 'sql-init-scripts'), ('extensions',), ('scripting',), ('translations',) }:
			sd = path_sm / pathlib.Path(*d)
			if (package / sd).exists():
				shutil.copytree(package / sd, args.directory / sd, dirs_exist_ok = True)
		
		if args.no_upgrade_plugins:
			print("Skipping install of plugins.")
		else:
			# map installed plugin filenames to paths; copy unknown files to disabled
			target_plugin_dir = args.directory / path_sm / 'plugins'
			installed_plugins = { f.name: f.parent for f in target_plugin_dir.rglob("*.smx") }
			for plugin in (package / path_sm / 'plugins').rglob("*.smx"):
				target = installed_plugins.get(plugin.name, target_plugin_dir / 'disabled')
				shutil.copyfile(plugin, target / plugin.name)
				
				print(plugin.name, 'copied to', target.relative_to(args.directory / path_sm))
		print("Upgrade complete.")

if __name__ == "__main__":
	main()
