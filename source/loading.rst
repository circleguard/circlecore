Loading
=======


|Replay|s
---------

When you instantiate a |Replay|, it doesn't have replay data, know the username or user id of who played it,
know mods it was played with, or have very much information about itself at all.

Some |Replay|s like |ReplayMap| have a little more information, because you passed it explicitly - a |ReplayMap|
knows the map id and user id of the replay, as well if the mods, if passed, and a |ReplayID| knows the id of its
replay.

Let's illustrate this by trying to access these attributes of replays directly after instantiation:

.. code-block:: python

    r_path = ReplayPath("/path/to/your/osr.osr")
    r_map = ReplayMap(221777, 2757689)
    r_id = ReplayID(2177560145)

    print(r_path.path) # "/path/to/your/osr.osr"
    print(r_path.replay_data) # None
    print(r_path.map_id) # None
    print(r_path.user_id) # None
    print(r_path.replay_id) # None
    print(r_path.mods) # None

    print(r_map.replay_data) # None
    print(r_map.map_id) # 221777
    print(r_map.user_id) # 2757689
    print(r_map.replay_id) # None
    print(r_map.mods) # None

    print(r_id.replay_data) # None
    print(r_id.map_id) # None
    print(r_id.user_id) # None
    print(r_id.replay_id) # 2177560145
    print(r_id.mods) # None

But we can retrieve more information about a replay by "loading" it. A replay is called "unloaded" if it hasn't
been loaded yet, and "loaded" if it has.

To load a replay, use |cg.load|. Once the replay is loaded, most of these attributes will be filled with the
proper value:

.. code-block:: python

    cg = Circleguard("key")
    r_map = ReplayMap(221777, 2757689)
    cg.load(r_map)

    # now we can access the real values of all these attributes

    print(len(r_map.replay_data)) # 26614
    print(r_map.map_id) # 221777
    print(r_map.user_id) # 2757689
    print(r_map.replay_id) # 2832574010
    print(r_map.mods) # Mod.HDHR

.. warning::

    Circleguard usually requests information about the replay from the api in order to fill in the gaps,
    so a call to |cg.load| could take considerable (>100ms) time as it involves network requests.

Depending on the replay subclass, some attributes may never be available because of api limitations or
other issues. For instance, the api doesn't provide *any* information for a |ReplayID| besides its replay
data, so almost none of its attributes will be filled, even after loading it:

.. code-block:: python

    cg = Circleguard("key")
    r_id = ReplayID(2177560145)
    cg.load(r_id)

    print(len(r_id.replay_data)) # 20611
    print(r_id.map_id) # None
    print(r_id.user_id) # None
    print(r_id.replay_id) # 2177560145
    print(r_id.mods) # None

To find exactly what attributes a replay subclass provides before and after it's loaded, look at its class'
documentation.

|ReplayContainer|s
------------------

We've seen two stages (unloaded and loaded) with |Replay|s, but |ReplayContainer|s introduce a third stage between
the two, called "info loaded".

When a |ReplayContainer| is first instantiated, it is unloaded, just like a |Replay|. This means that it only knows
the information you've given it - its map id if it's a |Map|, or its user id if it's a |User|, for instance. It has
no idea what |Replay| objects it should have.

You can fix this by calling |load_info| on the |ReplayContainer|. After doing so, it becomes info loaded and knows
what |Replay| objects it has.

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, span="1-2")

    print(list(m)) # [] since it's not info loaded!

    cg.load_info(m)
    print(list(m)) # [ReplayMap(...), ReplayMap(...)]

But when a |ReplayContainer| is info loaded, its |Replay|s are not loaded. This is the distinction between the info
loaded and loaded stage; the former has unloaded replays, and the latter has loaded replays.

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, span="1-2")

    cg.load_info(m)
    for replay in m:
        print(replay.loaded) # False
        # because the replay is unloaded, we can't access
        # very many of its attributes:
        print(replay.replay_id) # None

    cg.load(m):
    for replay in m:
        print(replay.loaded) # True
        # but we can now
        print(replay.replay_id) # some number

When you call |load| on a completely unloaded |ReplayContainer| (that is, not even info loaded), it info loads
the |ReplayContainer|s for you before loading it. So the following are equivalent:

.. code-block:: python

    # method 1
    cg = Circleguard("key")
    m = Map(221777, span="1-2")
    cg.info_load(m)
    cg.load(m)

    # method 2 (preferred)
    cg = Circleguard("key")
    m = Map(221777, span="1-2")
    cg.load(m)


Creating Info Loaded |ReplayContainer|s
---------------------------------------

We provide convenience methods to create info loaded |ReplayContainer|s with |Circleguard|. They are |cg.Map|,
|cg.User|, and |cg.MapUser|. For example:

.. code-block:: python

    cg = Circleguard("key")
    m = cg.Map(221777, span="1-2")
    # since it's info loaded, we can iterate
    for r in m:
        print(r)

    # the above is shorthand for
    cg = Circleguard("key")
    m = Map(221777, span=("1-2")
    cg.load_info(m)
    for r in m:
        print(r)


Each of these methods takes the exact same arguments as instantiating the |ReplayContainer| normally.

Checking State
--------------

You can check whether a |Replay| or |ReplayContainer| is unloaded, loaded, or info loaded by checking the
``loaded`` and/or ``info_loaded`` attributes:

.. code-block:: python

    cg = Circleguard("key")

    m = Map(221777, span="1")
    print(m.info_loaded, m.loaded) # False, False
    cg.load_info(m)
    print(m.info_loaded, m.loaded) # True, False
    cg.load(m)
    print(m.info_loaded, m.loaded) # True, True

    r = ReplayMap(221777, 2757689)
    print(r.loaded) # False
    cg.load(r)
    print(r.loaded) # True
