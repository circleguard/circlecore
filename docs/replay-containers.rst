Replay Containers
=================

Whereas a |Replay| represents a single replay, a |ReplayContainer| represents a set of replays. This is useful for if you want to
operate over the entire leaderboard of a map, a user's top plays, etc.

Map
---

A |Map| represents a beatmap's top plays (ie leaderboard), as seen on the osu! website.

When instantiating a |Map|, you must specify which scores you want from the map via the ``span`` argument:

.. code-block:: python

    # top 3 replays on the map
    m1 = Map(221777, span="1-3")

    # first, second, and 85th replays on the map
    m2 = Map(221777, span="1-2, 85")

    # 10th, 11th, 20th, and 25th replays on the map
    m3 = Map(221777, spn="10, 11, 20, 25")

We can also select replays set with a certain mod combination:

.. code-block:: python

    # top 2 HR scores (this means ONLY HR, not "HR plus any other mod")
    m1 = Map(221777, span="1-2", mods=Mod.HR)

    # third best HDHR score
    m2 = Map(221777, span="3", mods=Mod.HDHR)

User
----

A |User| represents the top plays of a user, as seen on their profile.

Similar to a |Map|, you must specify which scores of the user you want, and you can optionally
specify a mod combination to receive scores set with only that mod:

.. code-block:: python

    # top 2 scores of the user
    u = User(2757689, span="1-2")

    # second and third best scores with only HD
    u = User(2757689, span="2-3", mods=Mod.HD)

Map User
--------

A |MapUser| represents all of a user's plays on a beatmap. This is often only one score if the user has only ever
played the map with a single mod combination, but could be more depending on how many times they've played the map
with different mods.

Unlike |Map| and |User|, you are not required to specify which scores you would like via ``span``. |MapUser| assumes you want all
of the scores the user has set on the beatmap:

.. code-block:: python

    # all replays by cookiezi on everything will freeze
    mu = MapUser(555797, 124493)

You can still optionally specify a ``span`` argument if you would like:

.. code-block:: python

    # only cookiezi's second best replay on everything will freeze
    mu = MapUser(555797, 124493, span="2")

Accessing Replays
-----------------

A |ReplayContainer| is iterable, so you can retrieve |Replay| instances contained by the |ReplayContainer| in the usual ways.

Index access:

.. code-block:: python

    m = Map(221777, "1-2")
    cg.load_info(m)
    print(m[0])

Iterating:

.. code-block:: python

    for replay in m:
        print(replay)

Creating a list from the |ReplayContainer| (or alternatively calling |all_replays|):

.. code-block:: python

    print(list(m))
    print(m.all_replays())

We've used a method above, |cg.load_info|, that we haven't introduced yet. We will cover this method on the very next page
(under :ref:`info-loading`).
