Representing Replays
====================

Before you can use circlecore to calculate statistics of replays or do other operations on replays, you need
to know how to represent replays.

All replay classes you can instantiate are subclasses of |Replay|. We cover each subclass below.

ReplayMap
---------

a |ReplayMap| represents a replay by a user on a map. For instance,

.. code-block:: python

    replay = ReplayMap(221777, 2757689)

represents the highest scoring replay by user ``2757689`` on map ``221777``.

To restrict this to a replay with a certain mod combination, specify a mods argument.
For instance, this represents specifically the ``HDHR`` play by the same user on the same map.

.. code-block:: python

    replay = ReplayMap(221777, 2757689, mods=Mod.HD + Mod.HR)

While in this case these are identical replays, there are times a user has two
available replays on a map, with different mods.

ReplayPath
----------

|ReplayPath| represents a replay stored locally in an ``osr`` file. For instance,

.. code-block:: python

    replay = ReplayPath("/path/to/your/replay.osr")

represents the replay in the file ``/path/to/your/replay.osr``.


Lesser Used Replays
-------------------

These replay classes are provided for situations that don't come up in normal usage. They ar documented here for completeness.

ReplayID
~~~~~~~~

A |ReplayID| represents a replay which is tied to a replay ID on osu! servers.

.. code-block:: python

    r = ReplayID(2177560145) # cookiezi on freedom dive

.. warning::

    We can only retrieve the replay data associated with a replay id due to limitations with the api.
    This means we do not know with what mods or on what map a |ReplayID| was played on. This limits
    what kinds of functions can be called on it - for instance, |cg.ur| and |cg.hits| both require
    knowing what beatmap the replay was played on, and will reject |ReplayID|s.


ReplayString
~~~~~~~~~~~~

A |ReplayString| represents a replay file which has been read into a string object.

.. code-block:: python

    replay_data_str = open("/path/to/your/replay.osr", "rb").read()
    replay = ReplayString(replay_data_str)
