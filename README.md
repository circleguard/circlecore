# Circleguard

This project ultimately aims to create a comprehensive, player-run cheat detection tool. A by no means complete list of cheats includes replay stealing, relax, replay editing, and timewarp.

As of the v1.3 release, this tool detects both replay stealing and remodding.

**Disclaimer: Neither the Circleguard organization nor any of the circleguard devs are associated with osu! or the official osu! staff in any way.**

## Getting Started

You will need to install [Python 3+](https://www.python.org/downloads/) if you don't have it already, and then install the dependencies for this project:

```bash
$ pip install -r requirements.txt
```

For those not well versed in git or command line, [here is a video walkthrough of setting the program up](https://www.youtube.com/watch?v=Ozs2grxUyHw), with timestamps in the description. Note that due to the beta state this program is in, some parts of the video may already be outdated by the time you watch it.


## Usage

There are two ways to use the program - purely through the CLI, or through a GUI.

### CLI

For the former, run the circleguard.py file with some or all of the following flags:

| Flag | Usage |
| --- | --- |
| -h, --help | displays the messages below |
| -m, --map | checks the leaderboard on the given beatmap id against each other |
| -u, --user | checks only the given user against the other leaderboard replays. Must be set with -m |
| --mods | Download and compare only replays set with the exact mods given. Any number of arguments can be passed, and the top -n (or the number of replays available for that combination, whichever is fewer) replays will be downloaded and compared for each argument. |
| -l, --local | compare scores under the replays/ directory to a beatmap leaderboard (if set with -m), a score set by a user on a beatmap (if set with -m and -u) or the other scores in the folder (default behavior) |
| -t, --threshold | sets the similarity threshold to print comparisons that score under it. Defaults to 20 |
| -a, --auto-threshold | sets the number of standard deviations from the average similarity the threshold will automatically be set to. Overrides -t  **Note: If more than ![formula](https://latex.codecogs.com/gif.latex?\frac{1}{2}&space;-&space;\frac{1}{2}&space;\mathbf{erf}\frac{a}{\sqrt{2}}) of the input is stolen this may cause false negatives** |
| -n, --number | how many replays to get from a beatmap. No effect if not set with -m. Defaults to 50. **Note: the time complexity of the comparisons scales with O(n^2)** |
| -c, --cache | if set, locally caches replays so they don't have to be redownloaded when checking the same map multiple times |
| -s, --silent | if set, you will not be prompted for a visualization of comparisons under the threshold. Results will still be printed |
| -v, --verify | Takes 3 positional arguments - map id, user1 id and user2 id. Verifies that the scores are steals of each other |

#### Some Examples

```bash
# compares https://osu.ppy.sh/u/1019489's replay on https://osu.ppy.sh/b/1776628 with the 49 other leaderboard replays
$ python circleguard.py -m 1776628 -u 1019489

# compares the top 57 leaderboard replays against the other top 57 replays (57 choose 2 comparisons)
$ python circleguard.py -m 1618546 -n 57

# compares the top 50 leaderboard replays against the other top 50 replays (50 choose 2 comparisons) and sets the threshold to be one standard deviation below the average similarity.
$ python circleguard.py -m 1618546 -n 50 -a 1.0

# compares all replays under replays/ with the top 50 scores on https://osu.ppy.sh/b/1611251
$ python circleguard.py -l -m 1611251

# compares all replays under replays/ with all other replays under replays/
$ python circleguard.py -l
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

The gui looks slightly different on every operating system. Here's how it should look on windows:

<img src="https://i.imgur.com/OJ4J9Wk.png">

When you click 'run' in the gui, keep an eye on the command line you started the gui from, because that acts as both stdout and stdin of the program (meaning it will display results there, instead of the gui).

## Methodology
This program compares the cursor positions of two replays to determine average distance between them. Since the times rarely match up perfectly between replays, the coordinates from one replay are interpolated from its previous and next position to estimate its position at a time identical to the other replay. By doing this we force all timestamps to be identical for easy comparison, at the cost of some precision.

If run with -c (or with the appropriate option checked in the GUI), downloaded replays will be lossily compressed to roughly half their original size with [wtc compression](https://github.com/circleguard/wtc-lzma-compressor) and then stored in a local databsae. This reduces the need to wait for API ratelimits if run again.

## Developement

This project is maintained by [tybug](https://github.com/tybug), [sam](https://github.com/samuelhklumpers), and [trafis](https://github.com/Smitty1298).

If you have feedback on the program, are interested in contributing, or just want to keep an eye on developement, you can find our discord server here: https://discord.gg/VNnkTjm. We're a friendly bunch and would love any help you can offer!

## Credits

Thanks to [kszlim](https://github.com/kszlim), whose [replay parser](https://github.com/kszlim/osu-replay-parser) formed the basis of [our modified replay parser](https://github.com/circleguard/osu-replay-parser).

Thanks to [Accalix](https://twitter.com/Accalix_) for creating our logo!  You can check out more of his work and purchase commissions [here](https://accalixgfx.com/index.php)
