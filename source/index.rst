
Circlecore
==========
Circlecore is a both a cheat detection library and a utilities library for osu!. Features include:

* Replay Stealing / Remodding detection
* Unstable Rate (ur) calculation, for relax cheats
* Finding suspicious movements in replays (called Snaps), for aim correction cheats
* Frametime analysis, for timewarp cheats
* Hits calculation, which gives you a list of hits (where a replay hits a hitobject). This can be used to find edge hits, for example

Circleguard is developed and maintained by:

* `tybug <https://github.com/tybug>`__
* `samuelhklumpers <https://github.com/samuelhklumpers>`__

Installation
------------

Circlecore can be installed from pip:

.. code-block:: console

    $ pip install circleguard

.. note::

    This documentation refers to the project as ``circlecore`` to differentiate
    it from our organization `Circleguard <https://github.com/circleguard>`__
    and the gui application Circleguard_. However, ``circlecore`` is installed
    from pypi with the name ``circleguard``, and is imported as such in python
    (``import circleguard``).

Links
-----

| Github: https://github.com/circleguard/circlecore
| Documentation: https://circleguard.dev/docs/circlecore
| Discord: https://discord.gg/VNnkTjm


..
    couple notes about these toctrees - first one is to have a link back to the
    index page. the ``self`` keyword comes with its share of issues
    (https://github.com/sphinx-doc/sphinx/issues/2103), but none that matter
    that much to us. It's better than using ``index`` which works but generates
    many warnings when building.

    Hidden toctrees appear on the sidebar but not as text on the index page
    (this file).

.. toctree::
    :hidden:

    self

.. toctree::
    :maxdepth: 2
    :caption: Tutorials

    foreword
    representing-replays
    using-circleguard
    replay-containers
    loading
    caching

.. toctree::
    :caption: Contributing

    contributing

.. toctree::
    :caption: Appendix
    :hidden:

    appendix
