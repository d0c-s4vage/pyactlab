#!/usr/bin/env python
# encoding: utf-8

import os, sys
from setuptools import setup

setup(
    # metadata
    name='pyactlab',
    description='An interactive client for Active Collabe',
    long_description="""
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
    """,
    license='MIT',
    version='0.1',
    author='James Johnson',
    maintainer='James Johnson',
    author_email='d0c.s4vage@gmail.com',
    url='https://github.com/d0c-s4vage/pyactlab',
    platforms='Cross Platform',
	install_requires = [
		"requests",
                "xmltodict",
                "html2text",
                "markdown",
	],
    classifiers = [
        'Programming Language :: Python :: 2',
    ],
    scripts = [
        os.path.join("bin", "actlab"),
    ],
    packages = [
        "pyactlab", "pyactlab.lib"
    ]
)
