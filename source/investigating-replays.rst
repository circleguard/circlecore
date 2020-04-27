Investigating Replays
=====================

Circleguard
-----------

To investigate replays, you first need to create a |circleguard| object. To
do so you will need an api key.

If you don't already have an api key, visit https://osu.ppy.sh/p/api/ and enter
``Circleguard`` for ``App Name`` and
``https://github.com/circleguard/circlecore`` for ``App URL``. Circlecore
needs this key to retrieve replay data and user information, among other
things.

.. note::

    Due to a `redirection bug <https://github.com/ppy/osu-web/issues/2867>`_
    on the website, you may need to log in and refresh the page before being
    able to access the api page.

After that, circleguard instantion is easy:

.. code-block:: python

    cg = Circleguard("key")

Replace ``"key"`` in these examples with your api key.

Investigation
-------------

We provide several convenience methods through |circleguard| to investigate
replays for different cheat types.

For instance, to investigate replays for replay stealing, use |cg.steal_check|:

.. code-block:: python

    cg = Circleguard("key")
    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 4196808)
    replays = [r1, r2]
    results = cg.steal_check(replays)

and similarly for relax
(|cg.relax_check|) and aim correction
(|cg.correction_check|).

|cg.steal_check| (and other similar methods) returns a generator containing
|Result| objects. We will cover these shortly in :doc:`../results`.

Also important to note is that |Loadable|\s do not load any information from the
api on instantiation. |cg.run| is where this loading occurs, and where you
should expect api ratelimiting (when investigating 10 or more |Replay|\s) to
occur.

Should you want finer control over when you load replays, see
:doc:`../loading`.

.. note::

    |Loadable|\s that get loaded stay loaded, so you can reuse the same object
    without fear of doubling (or worse) the loading time.

Multiple Cheats
---------------

Should you want to investigate a replay for multiple cheats, you can always call
each of the methods we mentioned above on the replay. But we understand that
isn't enough for more advanced usage.

To investigate a replay for multiple cheats in one function call, you should
call |cg.run|, passing in a bitwise combination of |Detect| values.

For instance, to investigate a |Map| for both |Detect.RELAX| and
|Detect.CORRECTION|:

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, span="1-3")
    results = cg.run(m, Detect.RELAX | Detect.CORRECTION)
