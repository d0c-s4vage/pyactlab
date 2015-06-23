# pyactlab

pyactlab is an Active Collab project management system. It utilizes the Active
Collab API to provide a local directory structure to manage an Active Collab
project. Notebooks and pages created through the pyactlab interactive client
use a local git post-commit hook to push new changes to Active Collab, optionally
converting markdown to html.

pyactlab also provides an interactive Active Collab client for managing the project.
Currently supported project objects/actions are:

* tasks
* notebooks
* pages
* comments
* attachments
* screenshots

# Usage

## Installation

pyactlab can be installed directly from the master branch on github via `pip` with:

	pip install git+https://github.com/d0c-s4vage/pyactlab@master

## Project Initialization

Projects aren't currently creatable with the client. This should be done through the
Active Collab GUI.

Once a project is created, run the actlab script with `--init` to initialize a local
directory structure for the Active Collab project:

	actlab --init --url <URL+PATH+TO+ACTLAB>

![project initialization](http://i.imgur.com/8Pcacd0.gif)

## API Models

### API Model Creating

`actlab` allows you to create various Active Collab API models via the `create` command.

	create notebook

Creating the notebook does not perform any remote actions; it merely sets the current
Active Collab model to a new notebook with blank fields and lets you modify the fields
before saving it.

New models must be saved via the `save` command.

### API Model Editing

`actlab` maintains the state of the current Active Collab API model being used. The
current model can be viewed with the `show` command, and individual fields may be
set with the `set` command.

	show
	set name The New Name

Note that no quotes are needed after `set <field>` for values containing quotes.

If a field's value is set to `<`, then the current `$EDITOR` will be opened up with
a temporary file for the user to insert markdown into the field. This is useful for
multiline editing.

	create task
	set body <
	save

This also works well with comments:

	comment <

### API Model Listing

A project's models can be listed using the `list` command:

	list notebooks
	list tasks
	list comments

### API Model Selection

The current model may be set via the `use` command:

	actlab | Owner Company | Demo Project> list tasks
	[+]     1 - Test task
	actlab | Owner Company | Demo Project> use task 1
	[+]  fetched task
	actlab | Owner Company | Demo Project | Test task>

### API Model Navigation

Some models can only be accessed via a certain hierarchy. In order to
set the current model to a page inside the "test notebook" notebook, the test notebook must first
be selected, and then the page within the notebook may be selected.

In order to navigate out from under a hierarchy of models, use the `drop` command
to go up a level.

## Notebooks

`actlab` can create notebooks that are locally git-synced with the notebook's description in
the `notes` directory:

	create notebook
	set name SOME NOTEBOOK NAME
	save
	y

## Pages

`actlab` can create pages that a locally git-synced with a file in the `notes` directory.

	create page
	set name SOME PAGE NAME
	save
	y

## Tasks

`actlab` can create basic tasks:

	create task
	set name SOME TASK NAME
	set body <  // opens it up in $EDITOR
	save

`actlab` also has the `todo` command for quick task creation. Tasks created with `todo`
have "TODO" prefixed to the tasks name:

	todo check this out later

## Attachments

Many (most?) models in Active Collab support attachments. The `attach` command attaches
a file to the current actlab model.

	attach pics/screenshot1.png

Tab completion should work for existing files.

## Comments

Many models in Active Collab support comments. Comments may be added to the current model
by using  the `comment` command:

	comment This is a comment

If a longer comment is wanted (multiline), use the `<` special value for the comment
to open up a temporary file in `$EDITOR` which will then be used as the comment
value:

	comment <

Note that the contents of the temporary file are assumed to be in markdown format.

## Screenshots

Often during projects, screenshots are useful. I usually need to do a screenshot by
user-selected area. The `screen` command will start a relevant screenshot program that
will allow the user to select an area to be screenshotted, which will then be saved
to the specified filename within the `pics` directory.

	screenshot test_screenshot.png

Note that these are not automatically attached to the current model. This must be
done manually

## System Commands

Any unrecognized command will be treated as a system command. To explicitly execute
a system command, prefix the command with a bang `!`:

	!ls -la
	!pwd
