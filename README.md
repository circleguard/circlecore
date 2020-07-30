<img src="readme_resources/logo.png" alt="logo" width="200" height="200"/>

[![PyPi version](https://badge.fury.io/py/circleguard.svg)](https://pypi.org/project/circleguard/)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circlecore/badge)](https://www.codefactor.io/repository/github/circleguard/circlecore)

# Circlecore

Circlecore is a both a cheat detection library and a utilities library for osu!. Features include:

* Replay Stealing / Remodding detection
* Unstable Rate (ur) calculation, for relax cheats
* Finding suspicious movements in replays (called Snaps), for aim correction cheats
* Frametime analysis, for timewarp cheats

Built for use in [Circleguard](https://github.com/circleguard/circleguard), circlecore is easily integratable into any existing python project and we have worked hard to ensure it is easy to use. See [Usage](#Usage) (and our documentation at <https://circleguard.dev/docs/circlecore>) for developer guidance.

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)

## Installation

Circlecore can be installed from pip:

```bash
pip install circleguard
```

This documentation refers to the project as `circlecore` to differentiate it from our organization [Circleguard](https://github.com/circleguard) and the gui application [Circleguard](https://github.com/circleguard/circleguard). However, `circlecore` is installed from pypi with the name `circleguard`, and is imported as such in python (`import circleguard`).

## Links

Github: <https://github.com/circleguard/circlecore> <br/>
Documentation: <https://circleguard.dev/docs/circlecore> <br/>
Discord: <https://discord.gg/VNnkTjm> <br/>
Website: <https://circleguard.dev> <br/>

## Usage

We have documentation and a tutorial at <https://circleguard.dev/docs/circlecore>. However, below is a quickstart guide.

```python
from circleguard import *

# replace "key" with your api key
cg = Circleguard("key")
# replays by http://osu.ppy.sh/u/2757689 and http://osu.ppy.sh/u/4196808 on map
# http://osu.ppy.sh/b/221777
r1 = ReplayMap(221777, 2757689)
r2 = ReplayMap(221777, 4196808)

for result in cg.steal_check([r1, r2]): # r is a StealResult
    r = result
    print(f"{r.replay1.username} +{r.replay1.mods} vs {r.replay2.username} "
          f"+{r.replay2.mods} on {r.replay1.map_id}. {r.similarity} sim")

for result in cg.relax_check(r1): # r is a RelaxResult
    print(f"{r1}, {result.ur:.2f} ur")

for result in cg.correction_check(r2): # r is a CorrectionResult
    snap_times = [snap.time for snap in result.snaps]
    print(f"Number of snaps: {len(result.snaps)}, times: {snap_times}")

# ReplayMap isn't the only way to represent replays; we can also get a user's
# top 10 plays:
u = User(12092800, span="1-10")
# or a local replay:
r3 = ReplayPath("/path/to/local/osr/replay.osr")
# or all of a user's replays on a map:
mu = MapUser(221777, 2757689)
# and more...you can find them all at
# https://docs.circleguard.dev/en/v4.3.4/appendix.html#circleguard.loadable.Loadable.

# all of these can be investigated in the same way as ReplayMaps above, eg:
r = cg.steal_check([r, r3, mu])
# or just one:
r = cg.relax_check(u)

# there are more checks than just the above, as well - you can find them all at
# https://docs.circleguard.dev/en/v4.3.4/appendix.html#circleguard.circleguard.Circleguard
```

```python
from circleguard import *

cg = Circleguard("key")
m = Map(221777, span="1-2") # First two replays on 221777
# all Loadables (that is, anything that can be loaded - Map, User, ReplayMap,
# ReplayPath, etc) defer loading anything from the api until necessary.
# We can force the Map to load information about its replays:
cg.load_info(m)

# Once info loaded, we can iterate over Map, User, and MapUser to get the
# replays contained by them. Formally, these objects are called "LoadableContainers"
for replay in m:
    print(f"{replay.username} +{replay.mods} on map {replay.map_id}")

# the map is info loaded, but not yet loaded, so its replays are not yet loaded either
print(m[0].loaded) # False
print(m[0].replay_data) # None, unloaded replays don't yet have replay data
# we can force load m, which will load its replays:
cg.load(m)
print(len(m[0].replay_data)) # 11100

# all this loading is only necessary if you want to handle Loadables specially
# before checking them - cg.steal_check (and the other methods like cg.relax_check)
# automatically load the Loadables passed to them, which is why we didn't need
# to force load anything ourselves in the first example.
```

## Contributing

Join [our discord](https://discord.gg/VNnkTjm) and ask how you can help, or look around for open issues which interest you and tackle those. PR requests are welcome!
