Using Checks
============

A |Check| controls aspects of the investigation, such as thresholds and what
type of cheats to investigate for.

Instantiation
-------------

To instantiate a |Check|, pass an iterable containing |Loadable|\s. Remember
that |ReplayMap|, |ReplayPath|, |Map|, and |User| are all |Loadable|\s.

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)
    r2 = ReplayMap(221777, 4196808)
    l = [r1, r2]
    c = Check(l, detect=RelaxDetect())

Should you only have a single |Loadable| to investigate (common when using
|User| or |Map|), just the |Loadable| may be passed:

.. code-block:: python

    m = Map(221777, num=3)
    c = Check(m, detect=RelaxDetect())

    # an iterable still works
    c1 = Check([m], detect=RelaxDetect())

.. code-block:: python

    r1 = ReplayMap(221777, 2757689)
    c = Check([r1], detect=RelaxDetect())

Detect
~~~~~~

|Detect| lets you control exactly what circlecore is investigating the
|Loadable|\s in a |Check| for. You may only care about finding relax cheaters.
Additionally, some cheats are quicker to investigate for than others.

Each |Detect| subclass (|RelaxDetect|, |StealDetect|) corresponds to a cheat.
Each of these classes can be passed values on instantiation to be more or
less sensitive to suspicious plays. Replays below the threshold are considered
cheated, and replays above are considered legitimate.

.. note::

    We do not provide any finer level of granularity than a hard cutoff. If this
    is necessary to you, you will have to examine the |Result| in more detail.
    Read more at :ref:`understanding-results`.

|RelaxDetect|, for instance, defines a ur threshold. Should you want only
blatant relax cheats to be caught by circleguard, you might set the threshold
to 35.74, the `current ur world record <https://www.reddit.com/r/osugame/comments/8lqcyh/new_osustandard_ur_record_by_corim/>`_.
But if you're more skeptical (and okay with a higher false positive rate),
a threshold of 70 or 80 might be more appropriate.

.. code-block:: python

    r = ReplayMap(221777, 2757689)
    blatant_check = Check(r, RelaxDetect(30))
    suspicious_check = Check(r, RelaxDetect(80))

Combination
'''''''''''

We have only shown examples with |RelaxDetect| so far, but you can combine
|Detect|\s.

.. code-block:: python

    m = Map(221777, num=3)
    d = StealDetect(20) + RelaxDetect(50)
    c = Check(m, d)

.. note::

    Subtraction or other mathematical operators besides addition are not
    defined for |Detect|. Additionally, ``RelaxDetect(20) + RelaxDetect(30)``
    (for instance) is undefined behavior. Do not rely on adding the same
    |Detect| with different thresholds.

This |Check| defines an investigation into the |Map| for relax
(with a ur thresh of 50) and replay stealing (with a steal thresh of 20).
