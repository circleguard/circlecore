# osu!anticheat

This project ultimately aims to create a comprehensive, player-run anticheat. A by no means complete list of cheats includes replay stealing, relax, replay editing, and timewarp.

As of the v1.0 release, we only attempt to detect the first item in that list - replay stealing.

**Disclaimer: Neither the osu!ac organization nor any of the osu!anticheat devs are associated with osu! or the official osu! staff in any way.**

## Getting Started

You will need to install [Python 3+](https://www.python.org/downloads/) if you don't have it already, and then install the dependencies for this project:

```bash
$ pip install -r requirements.txt
```

For those not well versed in git or command line, [here is a video walkthrough of setting the program up](https://www.youtube.com/watch?v=Ozs2grxUyHw), with timestamps in the description. Note that due to the highly beta state this program is in, some parts of the video may already be outdated by the time you watch it.


## Usage

There are two ways to use the program - purely through the CLI, or through a GUI.

### CLI

For the former, run the anticheat.py file with some or all of the following flags:

| Flag | Usage |
| --- | --- |
| -h, --help | displays the messages below |
| -m, --map | checks the leaderboard on the given beatmap id against each other |
| -u, --user | checks only the given user against the other leaderboard replays. Must be set with -m |
| -l, --local | compare scores under the user/ directory to a beatmap leaderboard (if set with just -m), a score set by a user on a beatmap (if set with -m and -u) or other locally saved replays (default behavior) |
| -t, --threshold | sets the similarity threshold to print comparisons that score under it. Defaults to 20 |
| -n, --number | how many replays to get from a beatmap. No effect if not set with -m. Defaults to 50. **Note: the time complexity of the comparisons scales with O(n^2)** |
| -c, --cache | if set, locally caches replays so they don't have to be redownloaded when checking the same map multiple times |
| --single | compare all replays under user/ with all other replays under user/. No effect if not set with -l |
| -s, --silent | if set, you will not be prompted for a visualization of comparisons under the threshold. Results will still be printed |


#### Some Examples

```bash
# compares https://osu.ppy.sh/u/1019489's replay on https://osu.ppy.sh/b/1776628 with the 49 other leaderboard replays
$ python anticheat.py -m 1776628 -u 1019489

# compares the top 57 leaderboard replays against the other top 57 replays (57 choose 2 comparisons)
$ python anticheat.py -m 1618546 -n 57

# compares all replays under user/ with the top 50 scores on https://osu.ppy.sh/b/1611251
$ python anticheat.py -l -m 1611251

# compares all replays under user/ with all replays under compare/
$ python anticheat.py -l
```

This means that if you have a replay from a player and want to see if it's stolen, you should place it in the user/ directory and run with the -l and -m flags.

### GUI

The other option is to run gui.py with

```bash
 $ python gui.py
```

which will open a gui with roughly 1:1 inputboxes and checkboxes to the command line arguments.

The GUI often lags behind CLI implementations - a feature recently added to the latter may not be available on the former. This is because the GUI internally relies on the CLI implementation.

#### Examples

The gui looks slightly different on every operating system. Here's how it should look on mac:

<img src="https://i.imgur.com/5MQ9aP1.png">

When you click 'run' in the gui, keep an eye on the command line you started the gui from, because that acts as both stdout and stdin of the program (meaning it will display results there, instead of the gui).

## Methodology
This program compares the cursor positions of two replays to determine average distance between them. Since the times rarely match up perfectly between replays, the coordinates from one replay are interpolated from its previous and next position to estimate its position at a time identical to the other replay. By doing this we force all timestamps to be identical for easy comparison, at the cost of some precision.

If run with -c (or with the appropriate option checked in the GUI), downloaded replays will be lossily compressed to roughly half their original size with [wtc compression](https://github.com/osu-anticheat/wtc-lzma-compressor). This reduces the need to wait for API ratelimits if run again.

## Developement

This project is maintained by [tybug](https://github.com/tybug), [sam](https://github.com/samuelhklumpers), and [trafis](https://github.com/Smitty1298).

If you have feedback on the program, are interested in contributing, or just want to keep an eye on developement, you can find our discord server here: https://discord.gg/VNnkTjm. We're a friendly bunch and would love any help you can offer!

## Credits

Thanks to [kszlim](https://github.com/kszlim), whose [replay parser](https://github.com/kszlim/osu-replay-parser) formed the basis of [our modified replay parser](https://github.com/osu-anticheat/osu-replay-parser).
