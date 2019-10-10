# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

project = 'Circleguard'
copyright = '2019, Liam DeVoe, samuelhklumpers, InvisibleSymbol'
author = 'Liam DeVoe, samuelhklumpers, InvisibleSymbol'
release = '2.4.0'

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode"
]

intersphinx_mapping = {"python": ("https://docs.python.org/3", None),
                       "slider": ("https://llllllllll.github.io/slider/", None)}

html_theme = 'sphinx_rtd_theme'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# class references that we want to use easily in any file
rst_prolog = """
.. |ReplayMap| replace:: :class:`~circleguard.replay.ReplayMap`
.. |ReplayPath| replace:: :class:`~circleguard.replay.ReplayPath`
.. |Replay| replace:: :class:`~circleguard.replay.Replay`
.. |Check| replace:: :class:`~circleguard.replay.Check`
.. |cg.run| replace:: :func:`cg.run <circleguard.circleguard.Circleguard.run>`
.. |Result| replace:: :class:`~circleguard.result.Result`
"""
