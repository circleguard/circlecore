|ReplayContainer|s
==================

|Replay| subclasses work fine for some situations, but what if you wanted to calculate the unstable rate for all replays
on a map or in a user's top plays? You would have to make some api queries and manually construct |ReplayMap| objects.
Luckily, we provide classes that do this for you. They are called |ReplayContainer|s.

|Map|
-----

|Map|s represnt a beatmap's top plays (ie leaderboard), as seen on the osu! website.

When instantiating a |Map|, you must specify which of the scores you want from the map.

.. code-block:: python

    # top 3 replays on the map
    m1 = Map(221777, span="1-3")

    # first, second, and 85th replays on the map
    m2 = Map(221777, span="1-2, 85")

    # 10th, 11th, 20th, and 25th replays on the map
    m3 = Map(221777, spn="10, 11, 20, 25")

We can also select replays set with a certain mod combination.

.. code-block:: python

    # top 2 HR scores (this means ONLY HR, not "HR plus any other mod")
    m1 = Map(221777, span="1-2", mods=Mod.HR)

    # tihrd best HDHR scores
    m2 = Map(221777, span="3", mods=Mod.HDHR)

|User|
------

|User|s represent the top plays of a user, as seen on their profile.

Similar to a |Map|, you must specify which scores of the user you want, and you can optionally
specify a mod combination to receive scores set with only that mod.

.. code-block:: python

    # top 2 scores of the user
    u = User(2757689, span="1-2")

    # second and third best scores with only HD
    u = User(2757689, span="2-3", mods=Mod.HD)

|MapUser|
---------

|MapUser|s represent all of a user's plays on a beatmap. This is often only one score if the user has only ever
played the map with a single mod combination, but could be more depending on how many times they've played the map
with different mods.

Unlike |Map| and |User|, you do not have to specify which scores you would like - |MapUser| assumes you want all
of the scores the user has set on the beatmap. You can still optionally specify which scores you want.

.. code-block:: python

    cg = Circleguard("key")
    # all replays by cookiezi on everything will freeze
    mu = MapUser(555797, 124493)
    cg.load_info(mu)
    print(mu.all_replays()) # [ReplayMap(...,mods=NM,...), ReplayMap(...,mods=HDHR,...)]

    # only cookiezi's second best replay on everything will freeze
    mu = MapUser(555797, 124493, span="2")
    cg.load_info(mu)
    print(mu.all_replays()) # [ReplayMap(...,mods=HDHR,...)]


Notice that you cannot pass a ``mods`` argument to |MapUser|. This is intentional, because
``MapUser(221777, 2757689, mods=Mod.HDHR)`` (should that parameter exist) would return the identical replay as
``ReplayMap(221777, 2757689, mods=Mod.HDHR)``. ``ReplayMap`` usage is preferred in all cases.

You may have noticed a call to |cg.load_info| in the above code block. |ReplayContainer|s do not have any knowledge
about their replays when first instantiated, and must have information about them loaded before you can access their
replays. We cover this in more detail on the very next page.
