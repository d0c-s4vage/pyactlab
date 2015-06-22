#!/usr/bin/env python

import codecs
import distutils.spawn
import imp
import json
import os
import re
import subprocess
import sys

try:
	# realpath to get path symlinked path
	actlab_path = os.path.realpath(distutils.spawn.find_executable("actlab"))
	actlab = imp.load_source("actlab", actlab_path)
except Exception as e:
	print("actlab was not in $PATH, post-commit hook bailing")
	exit()

def git(*args):
	args = list(args)
	args = ['git'] + args
	git = subprocess.Popen(args, stdout = subprocess.PIPE)
	details = git.stdout.read()
	details = details.strip()
	return details

def get_changed_files():
	output = git("show", "--name-only", "HEAD")
	lines = output.split("\n")
	lines.reverse()

	files = []
	for line in lines:
		line = line.strip()
		if line == "":
			break
		files.append(line)
	
	return files

client = None
def handle_changes(fname):
	"""
	Look for the $$actlab marker in the file. The marker should be on a single line
	and should be followed by valid json
	"""
	git_root = git("rev-parse", "--show-toplevel")
	fpath = os.path.join(git_root, fname)

	with codecs.open(fpath, "rb", encoding="utf-8") as f:
		contents = f.read()
	
	marker = "$$actlab:"
	match = re.match(r'.*\$\$actlab:\s*({.*})\s*', contents)
	if match is not None:
		try:
			file_conf = json.loads(match.group(1))
		except:
			print("Could not parse actlab json config in file '{}'".format(fname))
			return

	# use this to find the config...
	os.chdir(git_root)
	clientShell = actlab.ActLabShell(None, load_models=False, y=True)
	actlab_config = clientShell.config

	client = actlab.pyactlab.ActLabClient(host=actlab_config.host, key=actlab_config.authkey)

	if "project" not in file_conf:
		print("no project specified, bailing")
		return

	pid = file_conf["project"]

	if "update" not in file_conf:
		print("no update field specified, bailing")
		return

	update_field = file_conf["update"]

	new_value = re.sub(r'.*\$\$actlab:\s*({.*}).*', "", contents)
	if fname.endswith(".md"):
		new_value = clientShell._md_to_html(new_value)

	if type(pid) is not int:
		print("project type must be int, value was '{}'".format(pid))
		return
	
	if "notebook" in file_conf:
		nid = file_conf["notebook"]
		if type(nid) is not int:
			print("notebook type must be int, value was '{}'".format(nid))
			return

		if "page" in file_conf:
			page_id = file_conf["page"]
			if type(pid) is not int:
				print("page type must be int, value was '{}'".format(page_id))
				return

			page = client.get_notebook_page(
				project_id=pid,
				notebook_id=nid,
				page_id=page_id
			)
			page[update_field] = new_value
			page.save()
			print("synced '{}' with page '{}'".format(fname, page.name))

		# we're just updating the notebook itself
		else:
			notebook = client.get_notebook(
				project_id=pid,
				notebook_id=nid
			)
			notebook[update_field] = new_value
			notebook.save()
			print("synced '{}' with notebook '{}'".format(fname, notebook.name))
	
	# we're updating the project itself
	else:
		project = client.get_project(project_id=pid)
		project[update_field] = new_value
		project.save()
		print("synced '{}' with project '{}'".format(fname, project.name))

if __name__ == "__main__":
	files = get_changed_files()
	for f in files:
		handle_changes(f)
