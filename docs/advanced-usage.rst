Advanced Usage
==============

This is a hodgepodge of circleguard features not mentioned in other parts of the documentation. This page is
written at a high level and is intended for developers who know what they are doing, and are just looking for a
page listing all the things they *can* do, or are looking to learn more about circleguard's internals.

Retrieve a Beatmap
------------------

To retrieve a beatmap from a replay, call |cg.beatmap|. This returns ``None`` if the replay cannot determine
what beatmap it was set on, and a |beatmap| otherwise.

Generate a Frametime Graph
--------------------------

To generate a frametime graph, call |cg.frametime_graph|. This is the same method that
`circleguard <https://github.com/circleguard/circleguard>`__ calls to generate its frametime graphs.

You must have matplotlib installed to use this method.

Utilities
---------

convert_statistic
~~~~~~~~~~~~~~~~~

|convert_statistic| converts a gameplay statistic such as unstable rate to its converted or unconverted form, given the mods
a replay was played with.

.. code-block:: python

    >>> convert_statistic(16, Mod.HDDT, to="cv")
    10.666666666666666
    >>> convert_statistic(16, Mod.HDDT, to="ucv")
    24
    >>> convert_statistic(16, Mod.NM, to="cv")
    16

A "statistic" in this context is anything modified by the game speed. So frametime and unstable rate are both "statistics"
that come in either a converted or unconverted form.

replay_pairs
~~~~~~~~~~~~

|replay_pairs| generates the pairs of replays which should be compared to cover all cases of replay stealing among the passed
sets of replays. See its documentation for more details.

fuzzy_mods
~~~~~~~~~~

|fuzzy_mods| returns all the mod combinations with the given required and optional mods:

.. code-block:: python

    >>> fuzzy_mods(Mod.HD, [Mod.DT])
    [HD, HDDT]
    >>> fuzzy_mods(Mod.HD, [Mod.EZ, Mod.DT])
    [HD, HDDT, HDEZ, HDDTEZ]
    >>> fuzzy_mods(Mod.NM, [Mod.EZ, Mod.DT])
    [NM, DT, EZ, DTEZ]

See its documentation for more details.

order
~~~~~

|order| returns 2-tuple of the given replays, with the replay that was played earlier first and the replay that was played later second.


Subclassing Replay
------------------

Subclassing |Replay| can be useful if you want to pull replay data from a source that circleguard doesn't support, or if
you want to customize the replay data processing. One common use case I can think of is providing a ``ReplayAkatsuki`` (or
(some similar class for another private server) which uses a private server's api to create a replay.

When sublcassing |Replay|, you must provide an implementation of the ``load`` method. You will also
want to consider overriding the ``beatmap`` and ``map_available`` methods, especially if your replay subclass
could be played on beatmaps that aren't available from the official osu! servers, or if you want to customize
where the beatmap gets loaded from. However, overriding these methods is not necessary. Only the ``load``
method must be provided.

load
~~~~

The ``load`` method is what circleguard calls to load the replay data of the replay. This method is responsible for retrieving the
replay's replay data from whatever data source it wants (an api, a replay file, a database, etc). Once it does so, it must call
``self._process_replay_data`` with the loaded replay data and set ``self.loaded`` to ``True``.

.. note::
    One philosophy of circleguard is that |Replay| objects are pseudo lazy loaded. That is, they are cheap to
    instantiate and only incur a cost when they need to be loaded. This is why we require that loading logic goes into
    its own ``load`` method instead of happening on instantiation.

``load`` takes two arguments: ``loader`` (a |Loader| instance) and ``cache`` (a boolean). ``loader`` provides you with access to
the api, should your replay need it. ``cache`` is ``True`` if the replay should be cached to the database once loaded, and
``False`` otherwise. You do not have to respect ``cache``, even if ``True``, if you do not want to (or cannot) implement caching
for your replay. For instance, we do not currently cache |ReplayPath| instances under any circumstances.

In order to facilitate replays which can be loaded without api access, ``loader`` may be null. If your replay needs api access
to load itself, and is passed a null ``loader``, raise an error:

.. code-block:: python

    if not loader:
        raise ValueError("A Map cannot be info loaded without api "
            "access")

If your replay does not need api access, you may safely ignore the ``loader`` argument.

The replay data that you pass to ``_process_replay_data`` must be a list of
`osrparse.ReplayEventOsu <https://github.com/kszlim/osu-replay-parser#attributes>`__ objects. You should convert your replay data
to instances of this class yourself if your data does not come as osrparse objects by default.

If your replay cannot load its replay data for whatever reason, pass ``None`` to ``_process_replay_data``. Do **not** pass an empty list,
as this has a different meaning (that the replay data is empty instead of unretrievable).

There are several attributes which you should always set if you can retrieve them. Some circleguard features will not work without these -
for instance, replays without a timestamp cannot be ordered, and replays without a map id cannot have their beatmap retrieved (unless you
provide an alternative ``beatmap`` method; more on this later). You can view a full list of these attributes in the |Replay| documentation.

For instance, |ReplayMap| makes api calls during its ``load`` method, which tells it the following attributes: ``timestamp``, ``username``,
``mods``, and ``replay_id``. So |ReplayMap| sets these attributes inside its ``load`` method (alongside ``game_version``, which it
can estimate from the timestamp):


.. code-block:: python

    self.timestamp = info.timestamp
    # estimate version with timestamp, this is only accurate if the user
    # keeps their game up to date
    self.game_version = GameVersion.from_datetime(self.timestamp,
        concrete=False)
    self.username = info.username
    self.mods = info.mods
    self.replay_id = info.replay_id

Your replay subclass should set as many of these attributes as your data source can provide.

beatmap
~~~~~~~

The purpose of this method is to return a |beatmap| representing the beatmap that this replay was played on.

Some circleguard methods require a |beatmap| to work properly (a currently exhaustive list is |cg.ur|, |cg.hits|, and
|cg.judgments|), or a beatmap can be optionally used to improve some statistical calculations. Whenever a beatmap is
required, |Circleguard| calls |replay.beatmap|, passing its |library| instance.

The default implementation of ``beatmap`` is to use the replay's map id and ask the passed |library| to retrieve the beatmap
with that id. If the replay does not provide a map id, the replay will be unable to provide a beatmap by default, since it doesn't
know what map it was played on.

To override this behavior, override ``beatmap`` and return either a |beatmap| object, or ``None`` if a beatmap could not be retrieved.

You can can query the passed library for the relevant beatmap if you find it useful, or you can ignore it in favor of retrieving the
beatmap another way. However, remember that at the end of the day you must return a |beatmap|. See slider's documentation
for more details on creating beatmaps from scratch, or from an osu! file, if you need them.

map_available
~~~~~~~~~~~~~

Return ``True`` if the replay *could* retrieve its beatmap if asked, and false otherwise. This is intended to be an inexpensive alternative
to calling ``beatmap`` and checking for a null response.

Subclassing ReplayContainer
---------------------------

To add a new |ReplayContainer|, you need only provide the ``load_info`` and ``all_replays`` methods.

Unless you know exactly what you're doing, you likely do **not** want to override ``load`` on a |ReplayContainer|. The default
implementation should be exactly what you want.

load_info
~~~~~~~~~

When called, the |ReplayContainer| should populate itself with |Replay| instances. It should only create them and not load them; they
will be loaded when ``ReplayContainer#load`` is called. A |Loader| instance is passed to this method to provide access to the api.

all_replays
~~~~~~~~~~~

A list of all replays in this |ReplayContainer|. This is provided to allow for arbitrarily complex storages of replays. For instance,
there might be a replay container which partitions its replay list into two sets, and stores those as separate attibutes. Such a
replay container would return the union of those sets in this method.

.. note::

    If the above instructions for subclassing |Replay| and |ReplayContainer| are unclear, you should look at the
    source code for examples. Every default |Replay| and |ReplayContainer| subclass is well abstracted and documented in the source
    code, and may be a clearer guide to follow than the above examples. See
    `<https://github.com/circleguard/circlecore/blob/master/circleguard/loadables.py>`__ for the file containing these classes.
