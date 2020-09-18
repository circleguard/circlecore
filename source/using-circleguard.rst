Using Circleguard
=================

Now you know how to represent replays, but how do we start calculating statistics or other information about them?
The answer is the |Circleguard| class.

To instantiate |Circleguard|, you will need an api key. If you don't already have one, visit https://osu.ppy.sh/p/api/
and enter ``Circleguard`` for ``App Name`` and ``https://github.com/circleguard/circlecore`` for ``App URL``.
Circleguard needs this key to retrieve replay data and user information, among other things.

.. note::

    Due to a `redirection bug <https://github.com/ppy/osu-web/issues/2867>`_
    on the website, you may need to log in and wait 30 seconds before being
    able to access the api page through the above link.

After you have your api key, circleguard instantion is easy:

.. code-block:: python

    cg = Circleguard("key")

Replace ``key`` in all codeblocks in this documentation with your api key.

|cg.similarity|
~~~~~~~~~~~~~~~

The similarity between two replays. Similarity is, roughly speaking, how
far apart in pixels the replays are on average.

.. code-block::

    cg = Circleguard("key")
    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 3219026)
    print(cg.similarity(r1, r2)) # 19.310565461539074

|cg.ur|
~~~~~~~

The unstable rate of the replay.

.. code-block::

    cg = Circleguard("key")
    r = ReplayMap(1136506, 846038)
    print(cg.ur(r)) # 75.45

    # you can also get the unconverted unstable rate
    print(cg.ur(r, cv=False)) # 113.18

|cg.snaps|
~~~~~~~~~~

Any unusual snaps in the cursor movement of the replay.

.. code-block:: python

    cg = Circleguard("key")
    r = ReplayMap(1136506, 6451401)
    print(cg.snaps(r)) # [<circleguard.investigator.Snap>]

    # you can adjust what counts as a "snap" by increasing
    # or decreasing these parameters. See |cg.snap|'s
    # documentation for details
    print(cg.snaps(r, max_angle=12, min_distance=6))
    # [<circleguard.investigator.Snap>, <circleguard.investigator.Snap>]

The list returned contains |Snap| objects. See its documentation for details.

|cg.frametime|
~~~~~~~~~~~~~~

The average frametime of the replay. Frametime is defined as the time (in ms)
between each frame and the frame after it.

.. code-block:: python

    cg = Circleguard("key")
    r = ReplayMap(1136506, 846038)
    print(cg.frametime(r)) # 15.33

    # you can also get the unconverted frametime
    print(cg.frametime(r, cv=False)) # 23.0

|cg.hits|
~~~~~~~~~

The locations in a replay where a hitobject is hit.

.. code-block:: python

    cg = Circleguard("key")
    r = ReplayMap(221777, 2757689)
    print(cg.hits(r)) # a list with lots of elements

The list returned contains |Hit| objects. See its documentation for details.

Other Replay Subclasses
~~~~~~~~~~~~~~~~~~~~~~~

The examples above have been using |ReplayMap| as their example replay, but you can pass any |Replay| subclass
to |Circleguard| methods:

.. code-block:: python

    cg = Circleguard("key")

    r1 = ReplayPath("/path/to/your/replay.osr")
    print(cg.ur(r1))

    r2 = ReplayMap(1754777, 2766034)
    print(cg.frametime(r2))

    r3 = ReplayID(2177560145)
    print(cg.snaps(r3))

    replay_data = open("/path/to/your/replay.osr", "rb").read()
    r4 = ReplayString(replay_data)
    print(cg.hits(r4))
