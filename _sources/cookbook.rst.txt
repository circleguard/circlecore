Cookbook
========

A collection of scripts for using circleguard, arranged in order from beginner to advanced. In
these examples, ``cg`` represents a |Circleguard| instance, and ``r`` represents any |Replay|
instance (eg, a |ReplayMap| or |ReplayPath|).

Save frametime graph as image
-----------------------------

.. code-block:: python

    cg.frametime_graph(r).gcf().savefig("plot.png")
