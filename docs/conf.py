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
copyright = "2020, Liam DeVoe, samuelhklumpers"
author = "Liam DeVoe, samuelhklumpers"
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

html_theme = "furo"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# references that we want to use easily in any file
rst_prolog = """
.. |Loadable| replace:: :class:`~circleguard.loadables.Loadable`
.. |Replay| replace:: :class:`~circleguard.loadables.Replay`
.. |ReplayMap| replace:: :class:`~circleguard.loadables.ReplayMap`
.. |ReplayDir| replace:: :class:`~circleguard.loadables.ReplayDir`
.. |ReplayPath| replace:: :class:`~circleguard.loadables.ReplayPath`
.. |ReplayString| replace:: :class:`~circleguard.loadables.ReplayString`
.. |ReplayID| replace:: :class:`~circleguard.loadables.ReplayID`
.. |ReplayContainer| replace:: :class:`~circleguard.loadables.ReplayContainer`
.. |Map| replace:: :class:`~circleguard.loadables.Map`
.. |User| replace:: :class:`~circleguard.loadables.User`
.. |MapUser| replace:: :class:`~circleguard.loadables.MapUser`

.. |all_replays| replace:: :func:`~circleguard.loadables.ReplayContainer.all_replays`

.. |RatelimitWeight| replace:: :class:`~circleguard.utils.RatelimitWeight`

.. |Circleguard| replace:: :class:`~circleguard.circleguard.Circleguard`
.. |cg.similarity| replace:: :func:`cg.similarity() <circleguard.circleguard.Circleguard.similarity>`
.. |cg.ur| replace:: :func:`cg.ur() <circleguard.circleguard.Circleguard.ur>`
.. |cg.snaps| replace:: :func:`cg.snaps() <circleguard.circleguard.Circleguard.snaps>`
.. |cg.frametime| replace:: :func:`cg.frametime() <circleguard.circleguard.Circleguard.frametime>`
.. |cg.frametimes| replace:: :func:`cg.frametimes() <circleguard.circleguard.Circleguard.frametimes>`
.. |cg.frametime_graph| replace:: :func:`cg.frametime_graph() <circleguard.circleguard.Circleguard.frametime_graph>`
.. |cg.hits| replace:: :func:`cg.hits() <circleguard.circleguard.Circleguard.hits>`
.. |cg.judgments| replace:: :func:`cg.judgments() <circleguard.circleguard.Circleguard.judgments>`

.. |cg.load| replace:: :func:`cg.load() <circleguard.circleguard.Circleguard.load>`
.. |cg.load_info| replace:: :func:`cg.load_info() <circleguard.circleguard.Circleguard.load_info>`
.. |cg.beatmap| replace:: :func:`cg.beatmap() <circleguard.circleguard.Circleguard.beatmap>`

.. |cg.Map| replace:: :func:`cg.Map() <circleguard.circleguard.Circleguard.Map>`
.. |cg.User| replace:: :func:`cg.User() <circleguard.circleguard.Circleguard.User>`
.. |cg.MapUser| replace:: :func:`cg.MapUser() <circleguard.circleguard.Circleguard.MapUser>`
.. |cg.ReplayMap| replace:: :func:`cg.ReplayMap() <circleguard.circleguard.Circleguard.ReplayMap>`
.. |cg.ReplayDir| replace:: :func:`cg.ReplayDir() <circleguard.circleguard.Circleguard.ReplayDir>`
.. |cg.ReplayPath| replace:: :func:`cg.ReplayPath() <circleguard.circleguard.Circleguard.ReplayPath>`
.. |cg.ReplayString| replace:: :func:`cg.ReplayString() <circleguard.circleguard.Circleguard.ReplayString>`
.. |cg.ReplayID| replace:: :func:`cg.ReplayID() <circleguard.circleguard.Circleguard.ReplayID>`

.. |replay.beatmap| replace:: :func:`replay.Beatmap() <circleguard.loadables.Replay.beatmap>`

.. |Snap| replace:: :class:`~circleguard.investigator.Snap`
.. |Hit| replace:: :class:`~circleguard.judgment.Hit`
.. |Judgment| replace:: :class:`~circleguard.judgment.Judgment`

.. |Span| replace:: :class:`~circleguard.span.Span`
.. |Loader| replace:: :class:`~circleguard.loader.Loader`

.. |convert_statistic| replace:: :func:`~circleguard.utils.convert_statistic`
.. |fuzzy_mods| replace:: :func:`~circleguard.utils.fuzzy_mods`
.. |replay_pairs| replace:: :func:`~circleguard.utils.replay_pairs`
.. |order| replace:: :func:`~circleguard.utils.order`

.. |library| replace:: :class:`slider.Library <slider.library.Library>`
.. |beatmap| replace:: :class:`slider.Beatmap <slider.beatmap.Beatmap>`

.. _Circleguard: https://github.com/circleguard/circleguard
.. _Circlecore: https://github.com/circleguard/circlecore
.. _tybug: https://github.com/tybug
.. _samuelhklumpers: https://github.com/samuelhklumpers
.. |br| raw:: html

   <br />
"""

# linebreak workaround documented here
# https://stackoverflow.com/a/9664844/12164878
