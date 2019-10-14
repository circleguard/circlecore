Convenience Methods
===================

Although circlecore allows you to define and investigate arbitrary |Replay|\s,
we provide so-called convenience methods for common use cases.

* map_check - investigate a map leaderboard
* verify - investigate two users for replay stealing on a single map
* user_check - investigate a user's top plays
* local_check - investigate osr files in a local folder

Map Check
---------

Investigates a map's leaderboard.

.. code-block:: python

    for r in cg.map_check(221777, detect=Detect.RELAX):
        print("this will print 50 times ", r.ur)

    for r in cg.map_check(221777, num=25, detect=Detect.RELAX):
        print("this will print 25 times ", r.ur)
