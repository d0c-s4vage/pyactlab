
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

# Installation

