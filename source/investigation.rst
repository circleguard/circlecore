Investigation
=============

Running Checks
--------------

A |Check| by itself doesn't do anything more than organize the |Detect| and
|Loadable|\s. To actually start an investigation, use |cg.run|.

.. code-block:: python

    m = Map(221777, num=3)
    d = StealDetect(20) + RelaxDetect(50)
    c = Check(m, d)

    cg = Circleguard("key")
    for r in cg.run(c):
        ...


|cg.run| is a generator returning |Result| objects. We will cover these shortly
in `Understanding Results`_.

It is important to note a bit about the internals of circlecore here.
As mentioned, |Loadable|\s do not load any information from the api on
instantiation. |cg.run| is where this loading occurs, and where you should
expect api ratelimiting (with more than 10 |ReplayMap|\s) to occur.

Should you want finer control over when you load replays, see |cg.load|, loads
a |Loadable|.

|Loadable|\s that get loaded stay loaded, so you can reuse the same object
without fear of doubling (or worse) the loading time.

.. code-block:: python

    cg = Circleguard("key")
    m = Map(221777, num=3)
    cg.load(m) # will take some time to load
    cg.load(m) # takes no time (already loaded)

    m2 = Map(221777, num=2)
    c = Check(m2, RelaxDetect())
    c2 = Check(m2, StealDetect())
    results = list(cg.run(c)) # will take some time to load
    # still takes some time (because of the steal investigation), but no wait due to loading
    results2 = list(cg.run(c2))

    # loading a check is the same as loading its loadables
    cg.load(m2) # takes no time; already loaded from cg.run()



.. todo::

    more detailed explanation in an Advanced section, but still talk briefly
    about the properties of loading here

.. _understanding-results:

Understanding Results
---------------------

A |Result| represent the result of the investigation into the |Check|
(and subsequently its |Loadable|\s). |Result| maps 1 to 1 with |Detect|—that is,
|StealDetect| yields |StealResult|, |RelaxDetect| yields |RelaxResult|, etc.
Should a combined |Detect| be passed, multiple |Result| types will be yielded.

There is no concept of a "combined result"—both of the |Result|\s from a mixed
|Detect| are yielded as their own object. Although circlecore could wait to
yield anything until the entire investigation is finished, because
investigations can take a significant amount of time, the program would have a
drought and subsequent flood of information.

Steal Result (Example)
~~~~~~~~~~~~~~~~~~~~~~

We will briefly cover |StealResult| as an example here. Look to the
documentation for the other |Result| classes for the attributes they provide.

The attributes available to us through |StealResult| are:

* ``replay1`` and ``replay2`` - the two |Replay| objects used in the
  comparison; in no meaningful order
* ``similarity`` - roughly speaking, the average distance in pixels between the
  two replays
* ``ischeat`` - whether ``similarity`` was below whatever threshold we set
* ``earlier_replay`` and ``later_replay`` - a reference to either ``replay1``
  or ``replay2`` respectively, depending on which one has an earlier
  ``timestamp``.

And here is how we might use a |StealResult|:

.. code-block:: python

    cg = Circleguard("key")
    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 4196808)
    c = Check([r1, r2], StealDetect(50))
    for r in cg.run(c): # r is a StealResult
        if not r.ischeat:
            print("replays by {r.replay1.username} and {r.replay2.username}"
                  "are not stolen")
            continue
        print(f"{r.later_replay.username}'s replay on map {r.later_replay.map_id}"
              f" +{r.later_replay.mods} is stolen from {r.earlier_replay.username}"
              f"with similarity {r.similarity}")

Play around with the threshold value and see how the print statement changes as
you decrease or increase the similarity. ie, as ``r.ischeat`` changes from
``True`` to ``False`` or vice versa.
