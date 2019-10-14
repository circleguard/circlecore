Understanding Results
=====================

|Result|\s provide information about an investigation made by circleguard. Each
|Result| subclass corresponds to a different type of cheat that
circlecore supports detecting,

Although you should look at a specific |Result|\s' documentation for the
attributes they have available, we will cover |ReplayStealingResult|
as an example here.

The attributes available to us through |ReplayStealingResult| are:

* ``replay1`` and ``replay2`` - the two |Replay| objects used in the
  comparison; in no meaningful order
* ``similarity`` - roughly speaking, the average distance in pixels between the
  two replays
* ``ischeat`` - whether ``similarity`` was below whatever threshold we set
* ``earlier_replay`` and ``later_replay`` - a reference to either ``replay1``
  or ``replay2`` respectively, depending on which one has an earlier
  ``timestamp``.

And here is how we might use a |ReplayStealingResult|:

.. code-block:: python

    cg = Circleguard("key")
    r1 = ReplayMap(221777, 2757689) # Toy
    r2 = ReplayMap(221777, 4196808) # Karthy
    c = Check([r1, r2], steal_thresh=50, detect=Detect.STEAL)
    for r in cg.run(c):
        if not r.ischeat:
            continue
        print(f"{r.later_replay.username}'s replay on map {r.later_replay.map_id}"
              f" +{r.later_replay.mods} is cheated with similarity {r.similarity}")

For demonstrational purposes, the threshold has been set to a very high ``50``
so circlecore will consider the comparison cheated.
