# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

project = "Circleguard"
copyright = "2019, Liam DeVoe, samuelhklumpers, InvisibleSymbol"
author = "Liam DeVoe, samuelhklumpers, InvisibleSymbol"
release = "2.4.0"
version = "2.4.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo"
]

intersphinx_mapping = {"python": ("https://docs.python.org/3", None),
                       "slider": ("https://llllllllll.github.io/slider/", None)}
# https://stackoverflow.com/a/37210251
autodoc_member_order = "bysource"

html_theme = "sphinx_rtd_theme"
# html_theme_options = {"display_version": False}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# references that we want to use easily in any file
rst_prolog = """
.. |Loadable| replace:: :class:`~circleguard.replay.Loadable`
.. |Replay| replace:: :class:`~circleguard.replay.Replay`
.. |ReplayMap| replace:: :class:`~circleguard.replay.ReplayMap`
.. |ReplayPath| replace:: :class:`~circleguard.replay.ReplayPath`
.. |ReplayContainer| replace:: :class:`~circleguard.replay.ReplayContainer`
.. |Map| replace:: :class:`~circleguard.replay.Map`
.. |User| replace:: :class:`~circleguard.replay.User`

.. |Check| replace:: :class:`~circleguard.replay.Check`
.. |Result| replace:: :class:`~circleguard.result.Result`
.. |RelaxResult| replace:: :class:`~circleguard.result.RelaxResult`
.. |StealResult| replace:: :class:`~circleguard.result.StealResult`

.. |Detect| replace:: :class:`~circleguard.enums.Detect`
.. |RelaxDetect| replace:: :class:`~circleguard.enums.RelaxDetect`
.. |StealDetect| replace:: :class:`~circleguard.enums.StealDetect`

.. |RatelimitWeight| replace:: :class:`~circleguard.enums.RatelimitWeight`

.. |cg.run| replace:: :func:`cg.run <circleguard.circleguard.Circleguard.run>`
.. |cg.load| replace:: :func:`cg.load <circleguard.circleguard.Circleguard.load>`
.. |cg.load_info| replace:: :func:`cg.load_info <circleguard.circleguard.Circleguard.load_info>`

.. _Circleguard: https://github.com/circleguard/circleguard
.. _osu!: http://osu.ppy.sh
.. _tybug: https://github.com/tybug
.. _samuelhklumpers: https://github.com/samuelhklumpers
.. _InvisibleSymbol: https://github.com/InvisibleSymbol
.. _osu api: https://github.com/ppy/osu-api/wiki
"""
