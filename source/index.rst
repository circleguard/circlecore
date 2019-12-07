
Circlecore
==========

Circlecore is a cheat detection library for `osu!`_.

Currently, we support the detection of the following cheats:

* Replay Stealing
* Relax
* Aim Correction

Designed for use in Circleguard_, circlecore is easily integratable into any
existing python project and we have worked hard to ensure it is easy to use.

We highly encourage projects that use circlecore - if you are using it in one
of your apps, please let us know and we will link to you somwhere in
our documentation.

Circlecore is developed and maintained by:

* tybug_
* samuelhklumpers_
* InvisibleSymbol_

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
| Documentation: https://circleguard.github.io/circlecore/
| Discord: https://discord.gg/VNnkTjm
| Website: https://circleguard.dev


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
    creating-checks
    investigation
    loading
    caching

.. toctree::
    :caption: Contributing

    contributing

.. toctree::
    :caption: Appendix
    :hidden:

    appendix
