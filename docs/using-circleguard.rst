Using Circleguard
=================

Now that we know how to represent replays, we can start operating on them. We will use the |Circleguard| class to do
so. |Circleguard| is the main entry point for this library, alongside the replay classes.

To instantiate |Circleguard|, you will need an api key. If you don't already have one, visit https://osu.ppy.sh/p/api/
and enter ``Circleguard`` for ``App Name`` and ``https://github.com/circleguard/circlecore`` for ``App URL``.
Circleguard needs this key to retrieve replay data and user information, among other things.

.. note::

    Due to a `redirection bug <https://github.com/ppy/osu-web/issues/2867>`_
    on the website, you may need to log in and wait 30 seconds before being
    able to access the api page through the above link.

After you have your api key, instantiate circleguard as follows:

.. code-block:: python

    cg = Circleguard("your-api-key)

Whenever you see ``cg`` in any codeblocks in this documentation, it refers to this circleguard instance.
We will omit this declaration from examples going forward to avoid duplicating it in every codeblock.

Similarity
----------

|cg.similarity| returns the similarity between two replays. Roughly speaking, this how far apart in pixels the
cursors in the replays are on average.

.. code-block::

    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 3219026)
    print(cg.similarity(r1, r2)) # 19.310565461539074

Unstable Rate
-------------

|cg.ur| returns the (converted) unstable rate of the replay.

.. code-block:: python

    r = ReplayMap(1136506, 846038)
    print(cg.ur(r)) # 75.45

You can also get the unconverted unstable rate:

.. code-block:: python

    print(cg.ur(r, cv=False)) # 113.18

Snaps
-----

|cg.snaps| returns any unusual, jerky, snappy cursor movement in a replay.

.. code-block:: python

    r = ReplayMap(1136506, 6451401)
    print(cg.snaps(r)) # [<circleguard.investigator.Snap>]

You can adjust what counts as "snap" with the ``max_angle`` and ``min_distance`` arguments. See the |cg.snaps|
documentation for details.

.. code-block:: python

    print(cg.snaps(r, max_angle=12, min_distance=6))
    # [<circleguard.investigator.Snap>, <circleguard.investigator.Snap>]

This returns a list of |Snap| objects. See the |Snap| documentation for details.

Frametime
---------

|cg.frametime| returns the average (converted) frametime of the replay. Frametime is defined as the time, in ms, between each frame and
the frame after it. Typical frametime is ``16.66``. A low frametime is indicative of timewarp (though not necessarily proof of timewarp; see
`<https://github.com/circleguard/circleguard/wiki/Frametime-Tutorial>`_).

.. code-block:: python

    r = ReplayMap(1136506, 846038)
    print(cg.frametime(r)) # 15.33

You can also get the unconverted frametime:

.. code-block:: python

    print(cg.frametime(r, cv=False)) # 23.0

Frametimes
----------

|cg.frametimes| returns the list of (converted) frametimes in the replay. This is useful for performing more advanced analysis
on a replay's frametime, beyond just its average frametime.

.. code-block:: python

    r = ReplayMap(1136506, 846038)
    print(cg.frametimes(r)) # [16. 8.67 ... 16.67 16.67]

You can also get the unconverted frametime:

.. code-block:: python

    print(cg.frametimes(r, cv=False)) # [24 13 ... 25 25]

Judgments
---------

The locations in a replay where a hitobject is hit or missed. Judgments are marked as either misses, 50s, 100s, or 300s. See |cg.judgments|.

.. code-block:: python

    r = ReplayMap(221777, 2757689)
    print(cg.judgments(r)) # a list with lots of elements

This returns a list of |Judgment| objects. See its documentation for details.


Hits
----

The locations in a replay where a hitobject is hit. This is equivalent to calling |cg.judgments| and filtering out misses. See |cg.hits|.

.. code-block:: python

    r = ReplayMap(221777, 2757689)
    print(cg.hits(r)) # a list with lots of elements

You can also get only the hits which are within a certain number of pixels to the edge of the hitobject:

    print(cg.hits(r, within=10)) # a list with fewer elements

This returns a list of |Hit| objects. See the |Hit| documentation for details.

Other Replay Classes
--------------------

The examples above have been using |ReplayMap| as their example replay, but you can pass any |Replay| class
to any |Circleguard| method:

.. code-block:: python

    r1 = ReplayPath("/path/to/your/replay.osr")
    print(cg.ur(r1))

    r2 = ReplayMap(1754777, 2766034)
    print(cg.frametime(r2))

    r3 = ReplayID(2177560145)
    print(cg.snaps(r3))

    replay_data = open("/path/to/your/replay.osr", "rb").read()
    r4 = ReplayString(replay_data)
    print(cg.hits(r4))

    # or any combination of the above
