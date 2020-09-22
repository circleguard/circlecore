|ReplayContainer|\s
===================

|Replay| subclasses work fine for some situations, but what if you wanted to calculate e.g. the unstable rate for all
replays on a map or in a user's top plays? You would have to make api requests and manually construct |ReplayMap|
objects. That would be annoying, so we provide classes that do this for you. They are called |ReplayContainer|\s.

|Map|
-----

|Map|\s represnt a beatmap's top plays (ie leaderboard), as seen on the osu! website.

When instantiating a |Map|, you must specify which scores you want from the map:

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

|User|
------

|User|\s represent the top plays of a user, as seen on their profile.

Similar to a |Map|, you must specify which scores of the user you want, and you can optionally
specify a mod combination to receive scores set with only that mod:

.. code-block:: python

    # top 2 scores of the user
    u = User(2757689, span="1-2")

    # second and third best scores with only HD
    u = User(2757689, span="2-3", mods=Mod.HD)

|MapUser|
---------

|MapUser|\s represent all of a user's plays on a beatmap. This is often only one score if the user has only ever
played the map with a single mod combination, but could be more depending on how many times they've played the map
with different mods.

Unlike |Map| and |User|, you do not have to specify which scores you would like - |MapUser| assumes you want all
of the scores the user has set on the beatmap. You can still optionally specify which scores you want:

.. code-block:: python

    cg = Circleguard("key")
    # all replays by cookiezi on everything will freeze
    mu = MapUser(555797, 124493)

    # only cookiezi's second best replay on everything will freeze
    mu = MapUser(555797, 124493, span="2")
    cg.load_info(mu)

Notice that you cannot pass a ``mods`` argument to |MapUser|. This is intentional, because
``MapUser(221777, 2757689, mods=Mod.HDHR)`` (should that parameter exist) would return the identical replay as
``ReplayMap(221777, 2757689, mods=Mod.HDHR)``. ``ReplayMap`` usage is preferred in all cases.

Iterating
---------

All |ReplayContainer|\s are iterable, so you can iterate over them to operate on their replays:

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, "1-2")
    cg.load_info(m)

    for r in m:
        print(r)

This means you can also create a list of replays from a |ReplayContainer| (or, equivalently, call |all_replays|):

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, "1-2")
    cg.load_info(m)

    print(list(m)) # [ReplayMap(...), ReplayMap(...)]
    print(m.all_replays()) # [ReplayMap(...), ReplayMap(...)]

But what are these mysterious |cg.load_info| methods? When you instantiate a |ReplayContainer|, it doesn't have any
|Replay| objects you can iterate over, because it hasn't made any api calls to determine which |Replay| objects
(by who, on what map) it should have. By calling |cg.load_info|, you are telling it to make these api calls and load
the info about its replays so you can iterate over them. We cover this (and loading in general) in more detail on
the very next page.
