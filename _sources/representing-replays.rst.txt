Representing Replays
====================

Before you can use circleguard to calculate statistics of replays or do other operations on replays, you need
to know how to represent replays.

All replay classes you can instantiate are subclasses of |Replay|. We cover each class below.

Replay Map
----------

A |ReplayMap| represents a replay by a user on a map. To get the highest scoring replay by the user
``2757689`` on the map ``221777``:

.. code-block:: python

    replay = ReplayMap(221777, 2757689)

To restrict this to a replay with a certain mod combination, use the ``mods`` argument. To get specifically the ``HDHR`` by
the same user as above:

.. code-block:: python

    replay = ReplayMap(221777, 2757689, mods=Mod.HD + Mod.HR)


Replay Path
-----------

A |ReplayPath| represents a replay stored locally in an ``osr`` file. To get the replay stored in the file
at ``/path/to/your/replay.osr``:

.. code-block:: python

    replay = ReplayPath("/path/to/your/replay.osr")


Replay ID
---------

A |ReplayID| represents a replay that was submitted online and is represented by a unique replay id.

.. code-block:: python

    r = ReplayID(2177560145) # cookiezi on freedom dive

.. warning::

    We can only retrieve the replay data, and nothing else, for a |ReplayID| due to limitations with the api.
    This means we do not know with what mods or on what map a |ReplayID| was played on. This limits
    what kinds of functions can be called on it. For instance, |cg.ur| and |cg.hits| both require
    knowing what beatmap the replay was played on, and will reject a |ReplayID|.


Replay String
-------------

A |ReplayString| represents a replay file which has been read into a string object. This replay class is rarely used.

.. code-block:: python

    replay_data_str = open("/path/to/your/replay.osr", "rb").read()
    replay = ReplayString(replay_data_str)
