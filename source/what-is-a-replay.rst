What is a Replay?
=================

|Replay|\s are the most basic object in Circleguard. We define two
|Replay| subclasses, |ReplayMap| and |ReplayPath|, though we support users
subclassing |Replay| or its two subclasses.

ReplayMap
---------

|ReplayMap|\s represent a replay by a user on a map. For instance,

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)

represents the replay by user ``2757689`` on map ``221777``.

ReplayPath
----------

|ReplayPath|\s represent a replay stored locally in an ``osr`` file.
For instance,

.. code-block:: python

    r2 = ReplayPath("/Users/tybug/Desktop/replays/replay1.osr")


represents the replay stored at ``/Users/tybug/Desktop/replays/replay1.osr``.

Loading Replays
---------------

|Replay|\s do not load the actual replay data until run with
:meth:`cg.run <circleguard.circleguard.Circleguard.run>`, or you explicitly
load them with :meth:`cg.load <circleguard.circleguard.Circleguard.load>`.
This design principle of objects being as cheap as possible to create, and only
loading further data when necessary, is something that holds true throughout
circleguard.
