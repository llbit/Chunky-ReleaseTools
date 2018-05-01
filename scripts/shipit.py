#!/usr/bin/env python
# coding=utf-8
# Copyright (c) 2013-2018 Jesper Öqvist <jesper@llbit.se>
#
# This file is part of Chunky.
#
# Chunky is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Chunky is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with Chunky.  If not, see <http://www.gnu.org/licenses/>.

# This script automates release building and publishing for Chunky.

import warnings

import json
import sys
import praw
import re
import io
import traceback
import ftplib
import codecs
import os
import shutil
import platform
import random, string
import time
from subprocess import call, Popen, PIPE
from getpass import getpass
from datetime import datetime
from string import join
from os import path
from shutil import copyfile

import launchpadlib
from launchpadlib.launchpad import Launchpad

# Debug logging:
#import httplib2
#httplib2.debuglevel = 1

class Credentials:
	initialized = False
	credentials = {}
	path = ''

	def __init__(self, filepath):
		self.path = path.abspath(filepath)

	def init(self):
		if not self.initialized and path.exists(self.path):
			proc = Popen(['gpg', '--decrypt', self.path], stdout=PIPE)
			creds = proc.communicate()[0]
			self.credentials = json.loads(creds)
		self.initialized = True


	# Check if the key has a value in the credential store, otherwise
	# ask for user input.
	def get(self, key):
		self.init()
		if key not in self.credentials:
			self.credentials[key] = raw_input(key+': ')
			self.save()
		return self.credentials[key]

	def get_noninteractive(self, key):
		self.init()
		if key not in self.credentials:
			return None
		return self.credentials[key]

	def getpass(self, key):
		self.init()
		if key not in self.credentials:
			self.credentials[key] = getpass(prompt=key+': ')
			self.save()
		return self.credentials[key]

	def put(self, key, value):
		self.init()
		self.credentials[key] = value
		self.save()

	def remove(self, key):
		del self.credentials[key]
		self.save()

	def save(self):
		proc = Popen('gpg --output credentials.gpg -r jesper@llbit.se --encrypt'.split(), stdin=PIPE)
		proc.communicate(json.dumps(self.credentials))
		if proc.returncode is not 0:
			print("Warning: failed to encrypt credentials!")

class Version:
	regex = re.compile('^(\d+\.\d+(\.\d+)?)(-[a-zA-Z]*\.?\d*)?$')
	full = ''
	milestone = ''
	suffix = ''
	series = ''
	changelog = ''
	release_notes = ''
	notes_file = ''

	def __init__(self, version):
		self.full = version
		r = self.regex.match(version)
		if not r:
			print("Invalid version name: %s (expected e.g. 1.2.13-alpha1)" % version)
			sys.exit(1)
		self.milestone = r.groups()[0]
		self.suffix = r.groups()[2]
		self.series = join(self.milestone.split('.')[:2], '.')
		notes_fn = 'release_notes-%s.txt' % self.milestone
		notes_fn2 = 'release_notes-%s.txt' % self.full
		if not path.exists(notes_fn):
			if path.exists(notes_fn2):
				notes_fn = notes_fn2
			else:
				print("Error: release notes not found!")
				print("Please edit release_notes-%s.txt!" % self.milestone)
				sys.exit(1)
		if not path.exists(notes_fn2):
			copyfile(notes_fn, notes_fn2)
		else:
			notes_fn = notes_fn2
		try:
			with codecs.open(notes_fn, 'r', encoding='utf-8') as f:
				self.release_notes = f.read().replace('\r', '')
		except:
			print("Error: failed to read release notes!")
			sys.exit(1)

		self.notes_file = notes_fn

		try:
			# Load changelog.
			with codecs.open("ChangeLog.txt", 'r', encoding='utf-8') as f:
				f.readline() # Skip version line.
				first = True
				while True:
					line = f.readline().rstrip()
					if not line:
						if first:
							continue
						else:
							break
					self.changelog += line + '\n'
					first = False
		except:
			print("Error: could not read ChangeLog!")
			sys.exit(1)

		if not self.changelog:
			print("Error: ChangeLog is empty!")
			sys.exit(1)

	def jar_file(self):
		return 'chunky-core-%s.jar' % self.full

	def tar_file(self):
		return 'chunky-%s.tar.gz' % self.full

	def zip_file(self):
		return 'Chunky-%s.zip' % self.full

	def exe_file(self):
		return 'Chunky-%s.exe' % self.full

	def dmg_file(self):
		return 'Chunky-%s.dmg' % self.full

	def sign_files(self):
		sign_file(self.jar_file())
		sign_file(self.zip_file())
		sign_file(self.tar_file())
		sign_file(self.exe_file())
		sign_file(self.dmg_file())

def sign_file(filename):
	while True:
		passphrase = credentials.getpass('gpg passphrase')
		print("Signing build/" + filename)
		proc = Popen(['gpg',
				'--pinentry-mode', 'loopback',
				'--passphrase-fd', '0',
				'--detach-sig', 'build/' + filename], stdin=PIPE)
		proc.communicate(passphrase + "\n")
		if proc.returncode is not 0:
			credentials.remove('gpg passphrase')
			print("Failed to sign file: " + filename)
			if raw_input('Retry? [y/N] ') == 'y':
				continue
			else:
				sys.exit(1)
		break

# The following class is from https://stackoverflow.com/a/24176022/1250278
class cd:
	"""Context manager for changing the current working directory"""
	def __init__(self, newPath):
		self.newPath = os.path.expanduser(newPath)

	def __enter__(self):
		self.savedPath = os.getcwd()
		os.chdir(self.newPath)

	def __exit__(self, etype, value, traceback):
		os.chdir(self.savedPath)

# Runs a command and aborts build if it failed.
def check_call(description, command):
	if call(command) != 0:
		print("Error: %s failed! Aborting build." % description)
		sys.exit(1)

def build_release(version):
	if version.suffix:
		print("Error: non-release version string speicifed (remove suffix)")
		print("Hint: add the -snapshot flag to build snapshot")
		sys.exit(1)
	print("Ready to build version %s!" % version.full)
	if raw_input('Build release? [y/N] ') == 'y':
		check_call('Gradle build',
				['./gradlew', '--rerun-tasks', '-PnewVersion=' + version.full,
				'tarball', 'releaseJar', 'releaseZip', 'documentation', 'release'])
		check_call('Ant build', ['ant', '-Dversion=' + version.full, 'nsi', 'macApp'])
		check_call('NSIS', nsis(['Chunky.nsi']))
		# https://stackoverflow.com/a/7553878/1250278
		os.makedirs('dmgdir/.background')
		copyfile('dist/chunky-dmg.png', 'dmgdir/.background/background.png')
		copyfile('dist/DS_Store', 'dmgdir/.DS_Store')
		os.symlink('/Applications', 'dmgdir/Applications')
		copyfile('dist/Chunky.icns', 'dmgdir/.Volume.icns')
		check_call('DMG build',
				'genisoimage -V Chunky -D -R -apple -no-pad -o'.split() \
				+ ['build/Chunky-%s.dmg' % version.full, 'dmgdir'])
		shutil.rmtree('dmgdir') # Cleanup.
		version.sign_files()
	if raw_input('Publish to Launchpad? [y/N] ') == 'y':
		(is_new, exe, dmg, zip, jar) = publish_launchpad(version)
		patch_url(version, jar)
		write_release_notes(version, exe, dmg, zip)
	if raw_input('Publish to FTP? [y/N] ') == 'y':
		publish_ftp(version)
	if raw_input('Post release thread? [y/N] ') == 'y':
		post_release_thread(version)
	if raw_input('Update documentation? [y/N] ') == 'y':
		update_docs(version)

# Builds NSIS command line with given args.
def nsis(args):
	return ['wine', path.expanduser('~/nsis-3.03/makensis.exe')] + args

def build_snapshot(version):
	if not version.suffix:
		print("Error: non-snapshot version string speicifed (add suffix)")
		sys.exit(1)
	print("Ready to build snapshot %s!" % version.full)
	if raw_input('Build snapshot? [y/N] ') == "y":
		while call(['git', 'tag', '-a', version.full, '-m', 'Snapshot build']) != 0:
			if raw_input("Delete tag and try again? [y/N] ") == "y":
				if call(['git', 'tag', '-d', version.full]) == 0:
					continue
			sys.exit(1)
		check_call('snapshot build',
				['./gradlew', '--rerun-tasks', '-PnewVersion=' + version.full, 'releaseJar'])
	if raw_input('Publish snapshot to FTP? [y/N] ') == "y":
		publish_snapshot_ftp(version)
	if raw_input('Post snapshot thread? [y/N] ') == "y":
		post_snapshot_thread(version)

def reddit_login():
	while True:
		id = credentials.get('reddit client ID')
		secret = credentials.get('reddit client secret')
		try:
			ua_string = 'praw:se.llbit.chunky.releasebot:v1.1 (by /u/llbit)'
			refresh_token = credentials.get_noninteractive('refresh_token')
			if refresh_token:
				r = praw.Reddit(
						check_for_updates=False,
						client_id=id,
						client_secret=secret,
						redirect_uri='http://localhost:8181/q',
						refresh_token=refresh_token,
						user_agent=ua_string)
			else:
				r = praw.Reddit(
						check_for_updates=False,
						client_id=id,
						client_secret=secret,
						redirect_uri='http://localhost:8181/q',
						user_agent=ua_string)
				rand_str = join(random.choice(string.lowercase + string.digits) for i in range(10))
				url = r.auth.url(['read', 'submit', 'flair', 'modposts', 'modflair'], rand_str, 'permanent')
				print("state: %s" % rand_str)
				print("Visit the Reddit authorization URL:")
				print(url)
				code = raw_input('Enter access code (from result URL): ')
				refresh_token = r.auth.authorize(code)
				credentials.put('refresh_token', refresh_token)
			return r
		except:
			if raw_input('Login failed. Try again? [y/N] ') != "y":
				raise

def ftp_login():
	while True:
		user = credentials.get('ftp user')
		pw = credentials.getpass('ftp password')
		try:
			ftp = ftplib.FTP('ftp.llbit.se')
			ftp.login(user, pw)
			return ftp
		except ftplib.error_perm:
			credentials.remove('ftp user')
			credentials.remove('ftp password')
			print("Login failed, please try again")

def publish_snapshot_ftp(version):
	ftp = ftp_login()
	ftp.cwd('chunkyupdate')
	with open('build/ChunkyLauncher.jar', 'rb') as f:
		ftp.storbinary('STOR ChunkyLauncher.jar', f)
	with open('latest.json', 'rb') as f:
		ftp.storbinary('STOR snapshot.json', f)
	ftp.cwd('lib')
	with open('build/chunky-core-%s.jar' % version.full, 'rb') as f:
		ftp.storbinary('STOR chunky-core-%s.jar' % version.full, f)
	ftp.quit()

def publish_ftp(version):
	ftp = ftp_login()
	ftp.cwd('chunkyupdate')
	with open('build/ChunkyLauncher.jar', 'rb') as f:
		ftp.storbinary('STOR ChunkyLauncher.jar', f)
	with open('latest.json', 'rb') as f:
		ftp.storbinary('STOR latest.json', f)
	ftp.cwd('lib')
	with open('build/chunky-core-%s.jar' % version.full, 'rb') as f:
		ftp.storbinary('STOR chunky-core-%s.jar' % version.full, f)
	ftp.quit()

def publish_launcher(version):
	ftp = ftp_login()
	ftp.cwd('chunkyupdate')
	with open('build/ChunkyLauncher.jar', 'rb') as f:
		ftp.storbinary('STOR ChunkyLauncher.jar', f)
	ftp.quit()

def update_docs(version):
	version_links = 'build/version-%s.properties' % version.full
	if not path.exists(version_links):
		print('Error: can not update documentation because %s does not exist. You must publish to launchpad to generate this file.' % version_links)
		return
	docs_dir = 'docs'
	docs_repo = 'github.com/llbit/chunky-docs.git'
	if path.exists(docs_dir):
		with cd(docs_dir):
			check_call('git', ['git', 'pull'])
	else:
		check_call('cloning documentation repo',
				['git', 'clone', "https://%s" % docs_repo, docs_dir])
	copyfile(version_links, path.join(docs_dir, 'version.properties'))
	version_dir = '%s/docs/release/%s' % (docs_dir, version.full)
	if not path.exists(version_dir):
		os.mkdir(version_dir)
	with codecs.open('build/release_notes-%s.md' % version.full,'r',encoding='utf-8') as src:
		with codecs.open('%s/docs/release/%s/release_notes.md' % (docs_dir, version.full),
				'w', encoding='utf-8') as dst:
			dst.write('''Chunky %s
============

''' % version.full)
			dst.write(src.read())
	with cd(docs_dir):
		check_call('git', 'git add .'.split())
		check_call('git', ['git', 'commit', '-m', 'Release %s' % version.full])
		gh_user = credentials.get('github user')
		gh_token = credentials.getpass('github token')
		check_call('git',
				['git', 'push', 'https://%s:%s@%s' % (gh_user, gh_token, docs_repo), 'master'])

def lp_upload_file(version, release, filename, description, content_type, file_type):
	# TODO: handle re-uploads.
	FILE_TYPES = dict(
		tarball='Code Release Tarball',
		readme='README File',
		release_notes='Release Notes',
		changelog='ChangeLog File',
		installer='Installer file')
	print("Uploading %s..." % filename)
	while True:
		try:
			signature_fn = filename + '.sig'
			release_file = release.add_file(
				filename=filename,
				description=description,
				file_content=open('build/' + filename, 'rb').read(),
				signature_content=open('build/' + signature_fn, 'rb').read(),
				signature_filename=signature_fn,
				content_type=content_type,
				file_type=FILE_TYPES[file_type])
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print("File upload error (%s):" % exc_type)
			traceback.print_exception(exc_type, exc_value, exc_traceback)
			if raw_input("Upload failed. Choose fix: [r]etry or [m]anual upload? ") == "r":
				continue
			print("Upload %s (%s) manually. Press enter to continue." % (filename, description))
			raw_input()
		return 'https://launchpad.net/chunky/%s/%s/+download/%s' \
			% (version.series, version.milestone, filename)

def check_file_exists(filename):
	if not path.exists('build/' + filename):
		print("Error: required artifact %s not found!" % filename)
		sys.exit(1)
	if not path.exists('build/' + filename + '.sig'):
		print("Error: required signature for %s not found!" % filename)
		sys.exit(1)

def publish_launchpad(version):
	# Check that required files exist.
	check_file_exists(version.jar_file())
	check_file_exists(version.tar_file())
	check_file_exists(version.zip_file())
	check_file_exists(version.exe_file())
	check_file_exists(version.dmg_file())
	if raw_input('Publish to production? [y/N] ') == "y":
		server = 'production'
		service = launchpadlib.uris.LPNET_SERVICE_ROOT
	else:
		server = 'staging'
		service = launchpadlib.uris.STAGING_SERVICE_ROOT

	app_name = 'Releasebot'
	launchpad = Launchpad.login_with(app_name, server, 'lpcache')

	chunky = launchpad.projects['chunky']

	# Check if release exists.
	release = None
	for r in chunky.releases:
		if r.version == version.milestone:
			release = r
			print("Previous %s release found: will to upload additional files." % version.milestone)
			break

	is_new_release = release is None

	if release is None:
		# Check if milestone exists.
		milestone = None
		for ms in chunky.all_milestones:
			if ms.name == version.milestone:
				milestone = ms
				break

		# Create milestone (and series) if needed.
		if milestone is None:
			series = None
			for s in chunky.series:
				if s.name == version.series:
					series = s
					break
			if series is None:
				series = chunky.newSeries(
					name=version.series,
					summary="The current stable series for Chunky. NB: The code is maintained separately on GitHub.")
				print("Series %s created. Please manually update the series summary:" % version.series)
				print(series)

			milestone = series.newMilestone(name=version.milestone)
			print("Milestone %s created." % version.milestone)

		# Create release.
		release = milestone.createProductRelease(
			release_notes=version.release_notes,
			changelog=version.changelog,
			date_released=datetime.today())
		milestone.is_active = False
		print("Release %s created" % version.milestone)

	assert release is not None

	# Upload release files.
	jar_url = lp_upload_file(
		version,
		release,
		version.jar_file(),
		'Core Library',
		'application/java-archive',
		'installer')
	assert jar_url
	print(jar_url)
	tarball_url = lp_upload_file(
		version,
		release,
		version.tar_file(),
		'Source Code',
		'application/x-tar',
		'tarball')
	assert tarball_url
	print(tarball_url)
	zip_url = lp_upload_file(
		version,
		release,
		version.zip_file(),
		'Binaries',
		'application/zip',
		'installer')
	assert zip_url
	print(zip_url)
	dmg_url = lp_upload_file(
		version,
		release,
		version.dmg_file(),
		'Mac Bundle',
		'application/octet-stream',
		'installer')
	assert dmg_url
	print(dmg_url)
	exe_url = lp_upload_file(
		version,
		release,
		version.exe_file(),
		'Windows Installer',
		'application/octet-stream',
		'installer')
	assert exe_url
	print(exe_url)
	return (is_new_release, exe_url, dmg_url, zip_url, jar_url)

"output markdown"
def write_release_notes(version, exe_url, dmg_url, zip_url):
	text = '''## Downloads

* [Windows installer](%s)
* [Mac bundle](%s)
* [Cross-platform binaries](%s)
* [Only launcher (win, mac, linux)](http://chunkyupdate.llbit.se/ChunkyLauncher.jar)

## Release Notes

''' % (exe_url, dmg_url, zip_url)
	text += version.release_notes + '''

## ChangeLog

'''
	text += version.changelog
	with codecs.open('build/release_notes-%s.md' % version.full, 'w', encoding='utf-8') as f:
		f.write(text)
	with codecs.open('build/version-%s.properties' % version.full, 'w', encoding='utf-8') as f:
		f.write('''version=%s
exe.dl.link=%s
dmg.dl.link=%s
zip.dl.link=%s''' % (version.milestone, exe_url, dmg_url, zip_url))

"Set a Reddit submission to be an announcement"
def set_announcement(post):
	flair = next(x for x in post.flair.choices()
			if x['flair_css_class'] == 'announcement')['flair_template_id']
	post.flair.select(flair, 'announcement')

"post reddit release thread"
def post_release_thread(version):
	try:
		with codecs.open('build/release_notes-%s.md' % version.full, 'r', encoding='utf-8') as f:
			text = f.read()
	except IOError:
		print("Error: reddit post must be in build/release_notes-%s.md" % version.full)
		return
	r = reddit_login()
	post = r.subreddit('chunky').submit('Chunky %s released!' % version.full,
		selftext=text)
	set_announcement(post)
	post.mod.sticky()
	print("Submitted release thread!")

"post reddit release thread"
def post_snapshot_thread(version):
	r = reddit_login()
	post = r.subreddit('chunky').submit('Chunky Snapshot %s' % version.full,
		selftext='''## Snapshot %s

A new snapshot for Chunky is now available. The snapshot is mostly untested,
so please make sure to backup your scenes before using it.

[The snapshot can be downloaded using the launcher.](http://chunky.llbit.se/snapshot.html)

## Notes

*These are preliminary release notes for upcoming features (which may not be fully functional).*

%s

## ChangeLog

''' % (version.full, version.release_notes) + version.changelog)
	set_announcement(post)
	print("Submitted snapshot thread!")

"patch url into latest.json"
def patch_url(version, url):
	print("Patching latest.json")
	j = None
	with open('latest.json', 'r') as f:
		j = json.load(f)
	if not j:
		print('Error: could not read latest.json')
		sys.exit(1)
	libs = j['libraries']
	patched = False
	for lib in libs:
		if lib['name'] == version.jar_file():
			lib['url'] = url
			patched = True
			break
	if not patched:
		print('Error: failed to patch url in latest.json: core lib not found!')
		sys.exit(1)
	with open('latest.json', 'w') as f:
		json.dump(j, f)

### MAIN
version = None
options = {
	'ftp': False,
	'docs': False,
	'snapshot': False,
	'prawdebug': False,
	'launcher': False
}
for arg in sys.argv[1:]:
	if arg == '-h' or arg == '--h' or arg == '-help' or arg == '--help':
		print("usage: SHIPIT [COMMAND] [VERSION]")
		print("commands:")
		print("    -ftp         upload latest.json to FTP server")
		print("    -docs        update documentation")
		print("    -snapshot    build snapshot instead of release")
		print("    -launcher    upload the launcher to the FTP server")
		print("")
		print("This utility creates a new release of Chunky")
		print("Required Python libraries: launchpadlib, PRAW")
		print("Upgrade with >pip install --upgrade <PKG>")
		sys.exit(0)
	else:
		if arg.startswith('-'):
			matched = False
			for key in options.keys():
				if arg == '-'+key:
					options[key] = True
					matched = True
					break
			if not matched:
				print("Error: unknown command: %s" % arg)
				sys.exit(1)
		elif version is None:
			version = Version(arg)
		else:
			print("Error: redundant argument: %s" % arg)
			sys.exit(1)

try:
	credentials = Credentials(path.join('private', 'credentials.gpg'))

	if options['prawdebug']:
		r = reddit_login()
		post = r.subreddit('chunky').submit('Test post',
				selftext='Debugging the reddit bot.')
		print(post.flair.choices())
		set_announcement(post)
		sys.exit(0)

	if options['launcher']:
		publish_launcher(version)
		sys.exit(0)

	if version == None:
		version = Version(raw_input('Enter version: '))

	if options['ftp']:
		publish_ftp(version)
	elif options['docs']:
		update_docs(version)
	elif options['snapshot']:
		build_snapshot(version)
	else:
		build_release(version)
		if raw_input('Push git release commit? [y/N] ') == "y":
			gh_user = credentials.get('github user')
			gh_token = credentials.getpass('github token')
			main_repo = 'github.com/llbit/chunky.git'
			check_call('git',
					['git', 'push', 'https://%s:%s@%s' % (gh_user, gh_token, main_repo), 'master'])
			check_call('git',
					['git', 'push', 'https://%s:%s@%s' % (gh_user, gh_token, main_repo), version.full])
		print("All done.")
except SystemExit:
	raise
except:
	exc_type, exc_value, exc_traceback = sys.exc_info()
	print("Unexpected error:")
	traceback.print_exception(exc_type, exc_value, exc_traceback)
	print("Release aborted. Press enter to exit.")
	raw_input()

