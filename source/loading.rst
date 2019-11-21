Loading
=======

How |Loadable|\s act before and after being loaded is not immediately obvious,
and a misconception can result in hours of frustrated debugging. This section
tries to explain in greater detail how loading works and what you need to do
to get the information you need from a |Loadable|.

We will also introduce several useful methods and functionality in this
section.


.. _Additional Loading Methods:

Additional Loading Methods
--------------------------

|cg.load| will load a given |Loadable|. This happens naturally during |cg.run|,
but as we will see below, you may need to have a loaded |Loadable| before you
call |cg.run|.

.. code-block:: python

    cg = Circleguard("key")
    r = ReplayMap(221777, 2757689)
    print(r.loaded)
    cg.load(r)
    print(r.loaded)

|cg.load_info| will load the info of a given |ReplayContainer|. See
`Replay Containers`_ for exactly what that means. Like |cg.load|, this happens
naturally during |cg.run|, but you may need an info loaded |ReplayContainer|
before you call |cg.run|.

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, num=2)
    print(m.loaded)
    cg.load(m)
    print(m.loaded)


Stages
------

This is not an idea truly formalized in the codebase (yet), but is a useful
crutch of an explanation.

Different |Loadable|\s have different stages, where varying amounts of
information is available to you. Each stage requires loading more information
from the api, which can be an expensive operation. This is why we defer loading
until necessary.


Replays
~~~~~~~

A |Replay| has two stages. Upon instantiation it is unloaded, and when
either |cg.run| or |cg.load| is called on it (or a parent |Check|) it
become loaded.

When unloaded, a |Replay| has only the attributes you passed to it—``path``
for |ReplayPath| and ``user_id`` and ``map_id`` for |ReplayMap|, alongside any
optional arguments such as ``mods``. Technically, a
|Replay| has a few more attributes than this (such as |RatelimitWeight|), but
they are beyond the scope of this discussion.

This means that trying to access, say, the ``replay_data`` or ``replay_id`` of
an unloaded |Replay| will result in an error. This is usually not a problem,
since the replays are loaded through |cg.run| and you can access
``replay_data`` etc. from the yielded |Result|. However, if you need to know
further information about the replay before you call |cg.run|, use |cg.load|.
After loading a |Replay|, you can then acess its other attributes without
issue.

.. todo::

    link to advanced section where we do talk about ratelimitweight/etc

    have replay data be empty by default, maybe truly formalize the unloaded
    /loaded relationship as well

Replay Containers
~~~~~~~~~~~~~~~~~

A |ReplayContainer| is slightly more complicated, and has three stages. It
starts unloaded, becomes info loaded when |cg.load_info| is called on it
(or a parent |Check|), and becomes loaded when |cg.load| is called on it (or a
parent |Check|).

When unloaded, a |ReplayContainer| only has the attributes you passed to it—
``user_id`` for |User| and ``map_id`` for |Map|, alongside any optional
arguments such as ``mods``. This means you can't actually access any of the
|Replay|\s in the container—it hasn't loaded anything from the api, so it
only knows what you gave it.

When info loaded, a |ReplayContainer| contains unloaded |Replay|\s. This means
that their ``user_id``, ``map_id``, and ``mods`` are available, but not
``replay_data``. You can iterate over its |Replay| list if the data
in unloaded |Replay|\s is useful to you.

When loaded, a |ReplayContainer| contains loaded |Replay|\s.

Of course, calling |cg.load| on an unloaded |ReplayContainer| will "skip"
(from your perspective) the info loaded stage and make it loaded. It is not
required to call |cg.load_info| before |cg.load| on a |ReplayContainer|.


Iterating
---------

A |ReplayContainer| can be iterated over or indexed to access its |Replay|\s.
This will of course only work in its info loaded and loaded stages, with
different amounts of information available from the |Replay|\s for each stage.

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, num=1)
    for r in m:
        print("this will never be printed")
    cg.load_info(m)
    for r in m:
        print("this will be followed by False")
        print(r.loaded)
    cg.load(m)
    for r in m:
        print("this will be followed by True")
        print(r.loaded)

This example works identically for a |User|, just with the |Replay|\s
representing their top plays instead of the leaderboards of a map.




.. todo::

    have cg.load_info accept a check, have check implement load_info
