Results
-------

A |Result| represent the result of an investigation into one or more replays.
|Result| are yielded by the functions you would expect - that is,
|cg.steal_check| returns |StealResult|, |cg.relax_check| returns |RelaxResult|,
and |cg.correction_check| returns |CorrectionResult|.

Should you call |cg.run|, |Result|\s corresponding to the |Detect|\(s) you pass
will be yielded.

Steal Result (Example)
~~~~~~~~~~~~~~~~~~~~~~

We will briefly cover |StealResult| as an example here. Look to the
documentation for the other |Result| classes for the attributes they provide.

The attributes available to us through |StealResult| are:

* ``replay1`` and ``replay2`` - the two |Replay| objects used in the
  comparison; in no meaningful order
* ``similarity`` - roughly speaking, the average distance in pixels between the
  two replays
* ``earlier_replay`` and ``later_replay`` - a reference to either ``replay1``
  or ``replay2`` respectively, depending on which one has an earlier
  ``timestamp``.

And here is how we might use a |StealResult|:

.. code-block:: python

    cg = Circleguard("key")
    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 4196808)
    for r in cg.steal_check([r1, r2]): # r is a StealResult
        print(f"{r.replay1.username} +{r.replay1.mods} vs {r.replay2.username} "
              f"+{r.replay2.mods} on {r.replay1.map_id}. {r.similarity} sim")
