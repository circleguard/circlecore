Representing Replays
====================

Before you can investigate replays using circlecore, you need to know a few ways
to represent them.

.. note::

    All of the following objects are lazy-loaded. That is, they are as cheap
    as possible to instantiate, and only incur a loading penalty when
    necessary (see |cg.load|, |cg.load_info|, and |cg.run|).


Replay
------

A |Replay| is the most basic object of circlecore. One replay object represents
one play made by a user. We define two |Replay| subclasses.

ReplayMap
~~~~~~~~~

|ReplayMap| represents a replay by a user on a map. For instance,

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)

represents the highest scoring replay by user ``2757689`` on map ``221777``. To
restrict this to a certain replay, specify a mods argument. This represents
specifically the ``HDHR`` play by the same user on the same map.

.. code-block:: python

    r1 = ReplayMap(221777, 2757689, mods=Mod.HD + Mod.HR)

While in this case these are identical replays, there are times a user has two
available replays on a map, with different mods. Because of how osu! stores
replays, it is impossible to have two available replays with the same
mod combination.

ReplayPath
~~~~~~~~~~

|ReplayPath| represents a replay stored locally in an ``osr`` file. For
instance,

.. code-block:: python

    r2 = ReplayPath("/path/to/your/replay.osr")

represents the replay in the file ``/path/to/your/replay.osr``.

Replay Containers
-----------------

A |ReplayContainer| represents a set of replays. These classes are provided as
a convenience, so you don't have to instantiate dozens of |Replay|\s yourself.

The ``span`` argument is an easy way to represent ranges of replays. See |Span|
for more information.

Map
~~~

It is common to want to represent all, or a subset of, a map's leaderboard.

.. code-block:: python

    # top 2 scores on the map
    m = Map(221777, span="1-2")

We can filter by mods:

.. code-block:: python

    # top 3 scores with exactly HD (not HDDT or another variation). Due to
    # api restrictions, we do not provide fuzzy matching.
    m = Map(221777, span="1-3", mods=Mod.HD)

Or only represent some of the replays on the map:

.. code-block:: python

    # 1st, 4th, 5th, 6th top scores
    m = Map(221777, span="1, 4-6")


Users
~~~~~

Similar to |Map|, a |User| represents the top plays of a user.

.. code-block:: python

    # top 2 scores of the user
    u = User(2757689, span="1-2")

We can still filter by mods:

.. code-block:: python

    # top 3 scores with exactly HD (not HDDT or another variation). Due to
    # api restrictions, we do not provide fuzzy matching.
    u = User(2757689, span="1-3", mods=Mod.HD)

MapUser
~~~~~~~

A |MapUser| represents all of a user's replays on a map.

This is especially useful for remod checks, by comparing a user's top play on a
map to his other replays.

.. code-block:: python

    r_top = ReplayMap(221777, 2757689)
    r_remods = MapUser(221777, span="2-100") # skip first replay; that's r_top
    r_all = [r_top, r_remods]
