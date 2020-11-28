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

def iter_dir_files(root_dir):
	""" Generator that yields all files within a directory and subdirectories. """
	if not root_dir.exists() or not root_dir.is_dir():
		return
	for p in root_dir.iterdir():
		if p.is_dir():
			yield from iter_dir_files(p)
		elif p.is_file():
			yield p

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

if __name__ == "__main__":
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
	with urllib.request.urlopen(r) as remote:
		pkg = pathlib.Path(urllib.parse.urlsplit(remote.geturl()).path.split('/')[-1])
		print('Installing SourceMod package', pkg)
		with tempfile.NamedTemporaryFile(delete = False, suffix = ''.join(pkg.suffixes)) as local:
			shutil.copyfileobj(remote, local)
			tempname = local.name
	
	# we have to reopen our tempfile because of exclusive file access on Windows
	with deferred_file_remove(tempname, 'rb') as local, tempfile.TemporaryDirectory() as package:
		shutil.unpack_archive(local.name, package)
		
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
			shutil.rmtree(args.directory / sd)
			shutil.copytree(package / sd, args.directory / sd, dirs_exist_ok = False)
		
		# update the contents of `configs/sql-init-scripts/`, `extensions/`, `scripting/`,
		# `translations` without touching other existing files
		for d in { ('configs', 'sql-init-scripts'), ('extensions',), ('scripting',), ('translations',) }:
			sd = path_sm / pathlib.Path(*d)
			shutil.copytree(package / sd, args.directory / sd, dirs_exist_ok = True)
		
		# iterate over extracted plugins and copy existing ones to root, else copy to disabled
		for plugin in iter_dir_files(package / path_sm / 'plugins'):
			if not (args.directory / path_sm / 'plugins' / plugin.name).exists():
				shutil.copyfile(plugin, args.directory / path_sm / 'plugins' / 'disabled' / plugin.name)
				print(plugin.name, 'disabled')
			else:
				shutil.copyfile(plugin, args.directory / path_sm / 'plugins' / plugin.name)
				print(plugin.name, 'installed')
		print("Upgrade complete.")
