Loading
=======

Loading a Replay
----------------

When you instantiate a |Replay|, it doesn't have replay data, know the username or user id of who played it,
know mods it was played with, or have very much information about itself at all.

Some |Replay|\s like |ReplayMap| have a little more information, because you passed it explicitly. For example, a
|ReplayMap| knows the map id and user id of the replay (as well as the mods if passed), and a |ReplayID| knows the id of
its replay.

We can illustrate this by trying to access these attributes of replays directly after instantiation:

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

As you can see, not many attributes are available to us. However, we can retrieve more information about a replay by "loading" it.
A replay is called "unloaded" if it hasn't been loaded yet, and "loaded" if it has.

To load a replay, call |cg.load| on it. Once the replay is loaded, most of these attributes will be filled with the
proper value:

.. code-block:: python

    r_map = ReplayMap(221777, 2757689)
    cg.load(r_map)

    # now we can access the real values of these attributes

    print(len(r_map.replay_data)) # 26614
    print(r_map.map_id) # 221777
    print(r_map.user_id) # 2757689
    print(r_map.replay_id) # 2832574010
    print(r_map.mods) # Mod.HDHR

.. warning::

    Circleguard usually requests information about the replay from the api in order to fill in the gaps,
    so a call to |cg.load| could take considerable (>100ms) time as it involves network requests.

Depending on the replay class, some attributes may never be available due to api limitations or
other issues. For instance, the api doesn't provide *any* information for a |ReplayID| besides its replay
data, so almost none of its attributes will be filled, even after loading it:

.. code-block:: python

    r_id = ReplayID(2177560145)
    cg.load(r_id)

    print(len(r_id.replay_data)) # 20611
    print(r_id.map_id) # None
    print(r_id.user_id) # None
    print(r_id.replay_id) # 2177560145
    print(r_id.mods) # None

To find exactly what attributes a replay class provides before and after it's loaded, see its class'
documentation.

Implicit Loading
----------------

Whenever you pass a |Replay| to a |Circleguard| method (|cg.snaps|, |cg.hits|, |cg.judgments|, etc), |Circleguard|
implicitly loads that replay before calculating the relevant statistic. This means that you don't have to worry
about loading a replay before passing it to a circleguard method.

.. _info-loading:

Info Loading
------------

A |Replay| has two stages, "unloaded" and "loaded". A |ReplayContainer| introduces a third stage called "info loaded".

When a |ReplayContainer| is first instantiated, it is unloaded, just like a |Replay|. This means that it only knows
the information you've given it - its map id if it's a |Map|, or its user id if it's a |User|, for instance. It has
no knowledge of any |Replay| objects yet.

To ask the |ReplayContainer| to create its replay objects, call |cg.load_info| on the |ReplayContainer|. This will make the
|ReplayContainer| "info loaded", and its replays can then be retrieved:

.. code-block:: python

    m = Map(221777, span="1-2")

    print(list(m)) # [] since it's not info loaded!

    cg.load_info(m)
    print(list(m)) # [ReplayMap(...), ReplayMap(...)]

The reason this does not happen by default / automatically is that info loading requires making api calls. This is a
(relatively) expensive operation and so is deferred until explicitly requested.

An important distinction is that when a |ReplayContainer| is info loaded, its |Replay| objects are not loaded. A
|ReplayContainer| only has loaded |Replay| objects when it is fully loaded:

.. code-block:: python

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

When you call |cg.load| on a completely unloaded |ReplayContainer| (that is, not even info loaded), it info loads
that |ReplayContainer| for you before loading it. So the following are equivalent:

.. code-block:: python

    # good
    m = Map(221777, span="1-2")
    cg.load(m)

    # bad
    m = Map(221777, span="1-2")
    cg.info_load(m)
    cg.load(m)


Creating Loaded Replays or ReplayContainers
-------------------------------------------

Creating a |Replay| and then loading it immediately afterwards is a common operation. We provide convenience methods
|cg.ReplayMap|, |cg.ReplayID|, |cg.ReplayPath|, and |cg.ReplayString| to create a loaded |Replay|:

.. code-block:: python

    r = cg.ReplayMap(221777, 4196808)
    print(r.loaded) # True
    # similarly for other replays
    r2 = cg.ReplayID(2177560145)
    r3 = cg.ReplayPath("/path/to/your/osr.osr")

Similarly, it is common to info-load a |ReplayContainer| it immediately after creating it. We provide analogous
convenience methods |cg.Map|, |cg.User|, and |cg.MapUser| to create an info-loaded |ReplayContainer|:

.. code-block:: python

    m = cg.Map(221777, "1-50")
    print(len(m)) # 50
    # similarly for other replay containers
    u = cg.User(124493, "1-2")
    mu = cg.MapUser(124493, 129891)

Each of these methods takes the exact same arguments as instantiating the relevant |Replay| or |ReplayContainer| normally.

Note that we do not currently provide convenience methods to create a loaded |ReplayContainer|, only info-loaded ones.

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
