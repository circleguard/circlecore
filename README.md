[![PyPi version](https://badge.fury.io/py/circleguard.svg)](https://pypi.org/project/circleguard/)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circlecore/badge)](https://www.codefactor.io/repository/github/circleguard/circlecore)
# Circlecore

Circlecore is a cheat detection library for osu!.

Circlecore currently supports detection of the following cheats:

* Replay Stealing
* Aim Correction

Designed for use in [Circleguard](https://github.com/circleguard/circleguard), circlecore is easily integratable into any existing python project and we have worked hard to ensure it is easy to use.

We highly encourage projects that use circlecore - if you are using it in one of your apps, please let us know and we will link to you somwhere in our readme or documentation.

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)
* [InvisibleSymbol](https://github.com/InvisibleSymbol)

## Installation

Circlecore can be installed from pip:

```bash
pip install circleguard
```

This documentation refers to the project as `circlecore` to differentiate it from our organization [Circleguard](https://github.com/circleguard) and the gui application [Circleguard](https://github.com/circleguard/circlegaurd). However, `circlecore` is installed from pypi with the name `circleguard`, and is imported as such in python (`import circleguard`).



## Usage

We have documentation and a tutorial at <https://circleguard.github.io/circlecore/>.

If you want a 30 second introduction to circlecore, see the following code snippets.

```python
cg = Circleguard("key")
r1 = ReplayMap(221777, 2757689)
r2 = ReplayMap(221777, 4196808)
c = Check([r1, r2], StealDetect(50))
for r in cg.run(c): # r is a StealResult
    if not r.ischeat:
        print("replays by {r.replay1.username} and {r.replay2.username} are not stolen")
        continue
    print(f"{r.later_replay.username}'s replay on map {r.later_replay.map_id} +{r.later_replay.mods}"
          f"is stolen from {r.earlier_replay.username} with similarity {r.similarity}")
```

```python
cg = Circleguard("key")
m = Map(221777, num=2)
cg.load_info(m)
for r in m:
    print(f"User {r.username} +{r.mods} on map {r.map_id}")
```
