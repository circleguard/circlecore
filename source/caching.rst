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
