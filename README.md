[![PyPi version](https://badge.fury.io/py/circleguard.svg)](https://pypi.org/project/circleguard/)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circlecore/badge)](https://www.codefactor.io/repository/github/circleguard/circlecore)
# Circlecore

Circlecore is a cheat detection library for osu!.

Circlecore currently supports detection of the following cheats:

* Replay Stealing
* Relax
* Aim Correction
* Timewarp

Designed for use in [Circleguard](https://github.com/circleguard/circleguard), circlecore is easily integratable into any existing python project and we have worked hard to ensure it is easy to use.

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)
* [InvisibleSymbol](https://github.com/InvisibleSymbol)

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

We have documentation and a tutorial at <https://circleguard.dev/docs/circlecore>.

If you want a 30 second introduction to circlecore, see the following code snippets.

```python
from circleguard import *

cg = Circleguard("key")
r1 = ReplayMap(221777, 2757689)
r2 = ReplayMap(221777, 4196808)
for r in cg.steal_check([r1, r2]): # r is a StealResult
    print(f"{r.replay1.username} +{r.replay1.mods} vs {r.replay2.username} "
          f"+{r.replay2.mods} on {r.replay1.map_id}. {r.similarity} sim")
```

```python
from circleguard import *

cg = Circleguard("key")
m = Map(221777, span="1-2")
cg.load_info(m)
for r in m:
    print(f"User {r.username} +{r.mods} on map {r.map_id}")
```
