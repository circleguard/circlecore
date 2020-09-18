# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# This will fail if circlecore's dependencies aren't installed.
# Which shouldn't be an issue because the only people running ``make html``
# (building the docs) are people with circlecore properly installed, hopefully.
from circleguard import __version__

project = "Circleguard"
copyright = "2019, Liam DeVoe, samuelhklumpers, InvisibleSymbol"
author = "Liam DeVoe, samuelhklumpers, InvisibleSymbol"
release = "v" + __version__
version = "v" + __version__
master_doc = 'index'

# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_show_copyright
html_show_copyright = False
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_show_sphinx
html_show_sphinx = False

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
.. |Loadable| replace:: :class:`~circleguard.loadables.Loadable`
.. |Replay| replace:: :class:`~circleguard.loadables.Replay`
.. |ReplayMap| replace:: :class:`~circleguard.loadables.ReplayMap`
.. |ReplayPath| replace:: :class:`~circleguard.loadables.ReplayPath`
.. |ReplayString| replace:: :class:`~circleguard.loadables.ReplayPath`
.. |ReplayID| replace:: :class:`~circleguard.loadables.ReplayPath`
.. |ReplayContainer| replace:: :class:`~circleguard.loadables.ReplayContainer`
.. |Map| replace:: :class:`~circleguard.loadables.Map`
.. |User| replace:: :class:`~circleguard.loadables.User`
.. |MapUser| replace:: :class:`~circleguard.loadables.MapUser`

.. |RatelimitWeight| replace:: :class:`~circleguard.utils.RatelimitWeight`

.. |Circleguard| replace:: :class:`~circleguard.circleguard.Circleguard`
.. |cg.similarity| replace:: :func:`~circleguard.circleguard.Circleguard.similarity`
.. |cg.ur| replace:: :func:`~circleguard.circleguard.Circleguard.ur`
.. |cg.snaps| replace:: :func:`~circleguard.circleguard.Circleguard.snaps`
.. |cg.frametime| replace:: :func:`~circleguard.circleguard.Circleguard.frametime`
.. |cg.frametimes| replace:: :func:`~circleguard.circleguard.Circleguard.frametimes`
.. |cg.hits| replace:: :func:`~circleguard.circleguard.Circleguard.hits`
.. |cg.load| replace:: :func:`~circleguard.circleguard.Circleguard.load`
.. |cg.load_info| replace:: :func:`~circleguard.circleguard.Circleguard.load_info`
.. |cg.Map| replace:: :func:`~circleguard.circleguard.Circleguard.Map`
.. |cg.User| replace:: :func:`~circleguard.circleguard.Circleguard.User`
.. |cg.MapUser| replace:: :func:`~circleguard.circleguard.Circleguard.MapUser`

.. |Span| replace:: :class:`~circleguard.span.Span`

.. _Circleguard: https://github.com/circleguard/circleguard
.. _Circlecore: https://github.com/circleguard/circlecore
.. _tybug: https://github.com/tybug
.. _samuelhklumpers: https://github.com/samuelhklumpers
"""
