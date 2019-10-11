
Circlecore
==========

Circlecore is a cheat detection library for `osu!`_

Currently, we support the detection of the following cheats:

* Replay Stealing
* Relax
* Aim Correction

Designed for use in Circleguard_, circlecore is easily integratable into any
existing python project and we have worked hard to ensure it is easy to use.

We highly encourage projects that use circlecore - if you are using it in one
of your apps, please let us know and we will link to you somwhere in
our documentation.

Circlecore is developed by tybug_, samuelhklumpers_, and InvisibleSymbol_.

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


.. toctree::
    :maxdepth: 2
    :caption: Tutorials

    what-is-a-replay
    using-checks
    understanding-results

.. toctree::
    :caption: Appendix
    :hidden:

    appendix
