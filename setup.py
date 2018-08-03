#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as f:
	long_description = f.read()

setuptools.setup(
	name="limittar",
	version="1.0",
	
	author="2sh",
	author_email="contact@2sh.me",
	
	description="Limiting the size of tar archives",
	long_description=long_description,
	long_description_content_type="text/markdown",
	
	url="https://github.com/2sh/limittar",
	
	packages=["limittar"],
	
	python_requires='>=3.4',
	classifiers=(
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
		"Operating System :: OS Independent",
		"Topic :: System :: Archiving"
	),
	
	entry_points={"console_scripts":["limittar=limittar:_main"]}
)
