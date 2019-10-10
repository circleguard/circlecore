Using Checks
============

To investigate |Replay|\s, we must first conglomerate them into a |Check|,
which handles aspects of the investigation such as cheat thresholds and what
types of cheats to check for.

.. code-block:: python

    c = Check([r1, r2], detect=Detect.STEAL)

To start an investigation into ``r1`` and ``r2``, use |cg.run|:

.. code-block:: python

    cg = Circleguard("key")
    for r in cg.run(c):
        ...

|cg.run| returns |Result| objects, representing the result of the investigation
into ``r1`` and ``r2``.
See :doc:`Understanding Results <../understanding-results>`
for more information.
