Understanding Results
=====================
Each |Result| subclass corresponds to a different type of cheat that
circlecore supports detecting. A full list of |Result|\s can be found under
the subclasses of :class:`~circleguard.result.Result`.

Although you should look at specific |Result|\s' documentation for the
attributes they have available, we will cover
:class:`~circleguard.result.ReplayStealingResult`\s as an example here.

The attributes available to us through
:class:`~circleguard.result.ReplayStealingResult` are:

* ``replay1`` and ``replay2`` (the two |Replay| objects used in the comparison;
  in no meaningful order)
* ``similarity`` - roughly speaking, the average distance in pixels between the
  two replays
* ``ischeat`` - whether ``similarity`` was below whatever threshold we set
