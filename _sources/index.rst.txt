Circlecore
==========

Circlecore is a utilities library for osu!. Features include:

* Unstable Rate calculation
* Judgments calculation (classifying all hitobjects into misses, hit300s, hit100s, hit50s, or sliderbreaks)
* Similarity calculation between two replays, for replay stealing detection
* Frametime calculation, for timewarp detection
* Jerky, suspicious movement detection (called Snaps)

Circlecore is used by `Circleguard <https://github.com/circleguard/circleguard>`__, a replay analysis tool.

Circlecore is developed and maintained by:

* `tybug <https://github.com/tybug>`__
* `samuelhklumpers <https://github.com/samuelhklumpers>`__

Installation
------------

Circlecore can be installed from pip:

.. code-block:: console

    $ pip install circleguard

.. note::

    This page refers to the project as ``circlecore`` to differentiate it from our organization
    `Circleguard <https://github.com/circleguard>`__ and our gui application Circleguard_. However, ``circlecore`` is installed
    from pypi with the name ``circleguard``, and is imported as such in python (``import circleguard``) We will also refer to it
    as ``circleguard`` for the remainder of the documentation.

Links
-----

| Github: https://github.com/circleguard/circlecore
| Documentation: https://circleguard.github.io/circlecore/
| Discord: https://discord.gg/VNnkTjm


..
    couple notes about these toctrees - the first toctree is so our sidebar has
    a link back to the index page. the ``self`` keyword comes with its share of
    issues (https://github.com/sphinx-doc/sphinx/issues/2103), but none that matter
    that much to us. It's better than using ``index`` which works but generates
    many warnings when building.

    Hidden toctrees appear on the sidebar but not as text on the table of contents
    displayed on this page.

.. toctree::
    :hidden:

    self

.. toctree::
    :maxdepth: 2
    :caption: Tutorial

    foreword
    representing-replays
    using-circleguard
    replay-containers
    loading
    caching
    advanced-usage

.. toctree::
    :caption: Contributing

    contributing

.. toctree::
    :caption: Appendix
    :hidden:

    appendix
