Caching
=======

Because the replay_data api endpoint is heavily ratelimited (10/min), we provide replay caching in |Circleguard|.
You can pass a ``db_path`` to |Circleguard| and any replay it loads will be cached there. This cache lives in an
(sqlite) ``.db`` file and will persist across runs.

.. code-block:: python

    cg = Circleguard("key", db_path="./cg_cache.db")

If the given path does not exist, circleguard will create fresh a db file there and use it. If the path is a
pre-existing databse file created by circleguard, that database will be used. Any other file existing at the path
will result in an error.

When loading a replay, we first check if the replay exists in the database, and load it from there if so. If not,
we load it from the api (or local file in the case of |ReplayPath|), compress the replays using
`WTC compression <https://github.com/circleguard/wtc-lzma-compressor>`_, and store in the database.

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 2757689)
    print("loading from api")
    cg.load(r1) # replay gets loaded from the api and cached
    print("loading from cache")
    cg.load(r2) # loaded from our cache, not the api
    # we can do this as many times as we want - we won't ever
    # hit the api ratelimit since we're loading from the cache
    for i in range(0, 5):
        print("loading from cache")
        r = ReplayMap(221777, 2757689)
        cg.load(r)

.. warning::

    WTC compression is lossy, so replays loaded from the api and loaded from cache will be slightly different.
    The loss is on the order of 0.1 precision in the xy coordinate of frames, which is not enough to impact
    the average use case, but could make a difference in some scenarios.

If you want to use a cache in read only mode (use previously cached replays, but don't cache new replays), pass
``cache=False`` to |Circleguard|:

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db", cache=False)

slider_dir
~~~~~~~~~~

We use `slider <https://github.com/llllllllll/slider>`_ to manage the download and parsing of beatmaps. We download beatmaps
when certain functions are called, such as |cg.hits|, that require the beatmap the replay was played on to work.

If ``slider_dir`` is passed, downloaded beatmaps will be cached to that directory (which must exist). You can use the same
directory the |Circleguard| cache db file is in if you'd like.

.. code-block:: python

    cg = Circleguard("key", db_path="./dbs/db.db", slider_dir="./dbs/")
    r = ReplayMap(221777, 2757689)
    cg.hits(r) # downloads https://osu.ppy.sh/b/221777 and caches it in slider_dir

If ``slider_dir`` is not passed, we still use slider to download beatmaps, but cache them to a newly created temporary directory
instead. This means beatmaps will be cached with respect to a single |Circleguard| object, but will not persist across runs.

Loadables
~~~~~~~~~

|Replay|\s and |ReplayContainer|\s also have a ``cache`` parameter, which determines if they should be cached when loaded.

.. note::

    The ``cache`` parameter has no effect if |Circleguard| was not passed a ``db_path`` or if |Circleguard| was
    instantiated with ``cache=False``.

This parameter is ``True`` by default, but by passing ``False`` we can selectively force certain loadables to not be cached
when they're loaded:

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    r1 = ReplayMap(221777, 2757689, cache=True)
    r2 = ReplayMap(1524183, 12092800, cache=False)
    cg.load(r1) # gets cached
    cg.load(r2) # does not get cached

For a |ReplayContainer|, ``cache`` cascades to its |Replay|\s:

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    m = Map(221777, span="1-2", cache=False)
    cg.load(m) # neither replay in `m` cached
