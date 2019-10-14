Using Checks
============

To investigate |Replay|\s, we must first conglomerate them into a |Check|,
which handles aspects of the investigation such as cheat thresholds and what
types of cheats to check for.

.. code-block:: python

    r1 = ReplayMap(221777, 2757689) # Toy
    r2 = ReplayMap(221777, 4196808) # Karthy
    c = Check([r1, r2])

By default, |Check|\s investigate |Replay|\s for every kind of cheat supported
by circlecore. This could be undesirable if you are only interested in catching
a specific type of cheat. To specify this, pass a |Detect| or combination
of |Detect|\s.

This can either be done at the |Replay| level:

.. code-block:: python

    r1 = ReplayMap(221777, 2757689, detect=Detect.RELAX)
    r2 = ReplayMap(221777, 4196808, detect=Detect.RELAX)
    c = Check([r1, r2])

or the |Check| level:

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 4196808)
    c = Check([r1, r2], detect=Detect.RELAX)

In the case of the latter, each of the replays will inherit their parent
|Check|'s |Detect| value, making these two code blocks functionally identical.

To combine |Detect|\s, use bitwise operators:

.. code-block:: python

    r1 = ReplayMap(221777, 2757689, detect=Detect.STEAL | Detect.RELAX)
    r2 = ReplayMap(221777, 4196808, detect=Detect.STEAL | Detect.RELAX)
    c = Check([r1, r2])

To start an investigation into ``r1`` and ``r2``, use |cg.run|:

.. code-block:: python

    cg = Circleguard("key")
    for r in cg.run(c):
        ...

|cg.run| returns |Result| objects, representing the result of the investigation
into ``r1`` and ``r2``. Depending on the |Detect| passed, these |Result|\s will
be different - :data:`Detect.RELAX <circleguard.enums.Detect.RELAX>` yields
|RelaxResult|, :data:`Detect.STEAL <circleguard.enums.Detect.RELAX>` yields
|ReplayStealingResult|, etc. If |cg.run| receives multiple |Detect|\s, a
mix of |Result|\s will be yielded, and it is your responsibility to type check
or otherwise ascertain which |Result| you are dealing with.
