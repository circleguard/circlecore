# osu!AntiCheat

This project is aimed at creating an anti-cheat for the rhythm game osu!. Currently it can detect cheaters who use Replay Stealing software (taking someone else's replay and submitting it as their own).

## Getting Started

You will need to install [Python 3+](https://www.python.org/downloads/) if you don't have it already, and then install the dependencies for this project:

```bash
$ pip install -r requirements.txt
```


## Usage

Currently, this repository can only detect replay stealers.

Run the program from the command line, with the following optional flags.

| Flag | Usage |
| --- | --- |
| -h, --help | displays the messages below |
| -m, --map | checks the leaderboard on the given beatmap id against each other |
| -u, --user | checks only the given user against the other leaderboard replays. Must be set with -m |
| -l, --local | compare scores under the user/ directory to a beatmap leaderboard (if set with just -m), a score set by a user on a beatmap (if set with -m and -u) or other locally saved replays (default behavior) |
| -t, --threshold | sets the similarity threshold to print comparisons that score under it. Defaults to 20 |
| -n, --number | how many replays to get from a beatmap. No effect if not set with -m. Defaults to 50. **Note: the time complexity of the comparisons scales with O(n^2)** |

### Some Examples

```bash
# compares https://osu.ppy.sh/u/1019489's replay on https://osu.ppy.sh/b/1776628 with the 49 other leaderboard replays
$ python anticheat.py -m 1776628 -u 1019489

# compares the top 57 leaderboard replays against the other top 57 replays (57 choose 2 comparisons)
$ python anticheat.py -m 1618546 -n 57

# compares all replays under user/ with the top 50 scores on https://osu.ppy.sh/b/1611251
$ python anticheat.py -l -m 1611251

# compares all replays under user/ with all replays under compare/
$ python anticheat.py
```

This means that if you have a replay from a player and want to see if it's stolen, you should place it in the user/ directory and run with the -l and -m flags.


## Methodology
- This program compares the x and y positions of two replays to determine the average distance apart of the cursors.
    -   Since the time's rarely match up perfectly, the coordinates from one replay are interpolated from two points in the other replay to estimate its position at the same time


## Developement

This project is currently maintained by [tybug](https://github.com/tybug), [sam](https://github.com/samuelhklumpers), and [trafis](https://github.com/Smitty1298). Developemental discussion is currently kept private but that may change with an official, working release of the program.
