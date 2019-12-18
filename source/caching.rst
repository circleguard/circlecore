Caching
=======

Circlecore provides a way to cache the replays and beatmaps downloaded from
the api.

db_path
~~~~~~~

If you provide a ``db_path`` to |Circleguard|, any replays loaded by it will
be cached. This cache lives in an (sqlite) ``.db`` file and will persist across
runs.

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")

The path is normalized with :class:`pathlib.Path`, so you can use relative
paths.

If the given path does not exist, circleguard will create a db file there
and use it. If the path is a pre-existing databse file created by circlecore,
that database will be used. Any other file existing at the path will result in
an error.

Caching occurs at the same time replays are loaded. This is usually when you
call |cg.run|, but also occurs during |cg.load| (see
:ref:`Additional Loading Methods`). Replays are first compressed using
`WTC compression <https://github.com/circleguard/wtc-lzma-compressor>`_,
then stored in the database. This reduces storage size with practically no
loss in precision, but note that because of this a cached replay's data will be
*almost* (but not quite) identical to that same replay, freshly loaded.

If you want to use a cache in read only mode (use previously cached replays,
but don't cache new replays), pass ``cache=False``. This has no effect on
the `slider_dir`_ argument. ``cache`` is ``True`` by default.

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db", cache=False)

slider_dir
~~~~~~~~~~

We use `slider <https://github.com/llllllllll/slider>`_ when working with
beatmaps. Currently, we only need to download beatmaps when |RelaxDetect| is
used. If ``slider_dir`` is passed, downloaded beatmaps will be cached to that
directory (which must exist). This directory may be the same directory the
replay's ``db.db`` is in.

.. code-block:: python

    cg = Circleguard("key", slider_dir="./dbs/")
    # can combine with db_path
    cg2 = Circleguard("key", db_path="./dbs/db.db", slider_dir="./dbs/")

If ``slider_dir`` is not passed, we still use slider to download beatmaps,
but cache them to a newly created temporary directory. This means it will cache
with respect to a single |Circleguard| object, but not persist across runs.

Loadable
~~~~~~~~

A |Loadable| also has a ``cache`` option, determing if the replays in that
|Loadable| should be cached when loaded. This has no effect if |Circleguard|
is not passed a ``db_path`` or is in read-only mode.

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    r1 = ReplayMap(221777, 2757689, cache=True)
    r2 = ReplayMap(221777, 2757689)
    cg.load(r1) # r gets cached
    cg.load(r2) # loaded from cache, not api

Passing ``cache=True`` is not very interesting in this scenario (that's
the default), but ``cache=False`` can selectively turn off caching for a
|Loadable|:

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    r1 = ReplayMap(221777, 2757689, cache=True)
    r2 = ReplayMap(1524183, 12092800, cache=False)
    cg.load(r1) # gets cached
    cg.load(r2) # does not get cached

For a |ReplayContainer|, ``cache`` cascades to its |Replay|\s.

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    m = Map(221777, num=2, cache=False)
    cg.load(m) # neither replay in Map cached

|Check| can also get passed ``cache``. If it contains a |ReplayContainer|,
the cache set by |ReplayContainer| takes precedence:

.. code-block:: python

    cg = Circleguard("key", db_path="./db.db")
    m = Map(221777, num=2, cache=False)
    u = User(2757689, num=3, cache=True)
    c = Check([m, u], detect=RelaxDetect(), cache=True)
    cg.load(c) # the 2 replays in m will not get cached, but the 3 replays in u will
