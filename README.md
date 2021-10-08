<img src="readme_resources/logo.png" alt="logo" width="200" height="200"/>

[![PyPi version](https://badge.fury.io/py/circleguard.svg)](https://pypi.org/project/circleguard/)

# Circlecore ([documentation](https://circleguard.github.io/circlecore/))

Circlecore is a utilities library for osu!. Features include:

* Unstable Rate calculation
* Judgments calculation (classifying all hitobjects into misses, hit300s, hit100s, hit50s, or sliderbreaks)
* Similarity calculation between two replays, for replay stealing detection
* Frametime calculation, for timewarp detection
* Jerky, suspicious movement detection (called Snaps)

Circlecore is used by [Circleguard](https://github.com/circleguard/circleguard), a replay analysis tool.

Circlecore is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)

## Installation

Circlecore can be installed from pip:

```bash
pip install circleguard
```

This documentation refers to the project as `circlecore` to differentiate it from our organization [Circleguard](https://github.com/circleguard) and the replay analysis tool [Circleguard](https://github.com/circleguard/circleguard). However, `circlecore` is installed from pypi with the name `circleguard`, and is imported as such in code (`import circleguard`).

## Links

Github: <https://github.com/circleguard/circlecore> <br/>
Documentation: <https://circleguard.github.io/circlecore/> <br/>
Discord: <https://discord.gg/VNnkTjm> <br/>

## Usage

We have a full tutorial and documentation at <https://circleguard.github.io/circlecore/>. If you really want to jump right in, below is a quickstart guide:

```python
from circleguard import *

# replace "key" with your api key
cg = Circleguard("key")
# replay on http://osu.ppy.sh/b/221777 by http://osu.ppy.sh/u/2757689
replay = ReplayMap(221777, 2757689)

print(cg.ur(replay)) # unstable rate
print(cg.frametime(replay)) # average frametime
print(cg.frametimes(replay)) # full frametime list
print(cg.hits(replay)) # where the replay hits hitobjects
print(cg.snaps(replay)) # any jerky/suspicious movement

replay2 = ReplayMap(221777, 4196808)
print(cg.similarity(replay, replay2)) # how similar the replays are

# ReplayMap isn't the only way to represent replays; we can also
# get a beatmap's top 3 plays
map_ = cg.Map(221777, span="1-3")
# or a User's fifteenth and twentieth best plays
user = cg.User(124493, span="15, 20")
# or a local replay
replay3 = ReplayPath("/path/to/local/osr/replay.osr")
# and more. You can find them all at
# https://circleguard.github.io/circlecore/appendix.html#circleguard.loadables.Loadable

# maps and users can be iterated over
for r in map_:
    print(cg.ur(r))
```

## Contributing

Join [our discord](https://discord.gg/VNnkTjm) and ask how you can help, or look around for open issues which interest you and tackle those. Pull requests are welcome!
