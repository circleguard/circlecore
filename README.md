# ReplaySBS

This project is aimed at trying to create an anti-cheat for the rhythm game osu!, specifically to catch cheaters who use Replay Stealing software. While it is nearly impossible to detect if someone uses their own replays to submit (whether edited or just sped up). Many people choose to steal other player's replays and submit them as their own instead. This program aims to catch these stolen replays. 

## Getting Started

You will need to install [Python 3+](https://www.python.org/downloads/) and use pip to install the osrparse module

```
pip install osrparse
```

You will also need to edit the path of the folders that hold the replays on your own machine to the top of the python file
On my machine it is as follows: 

```
pathToUserReplay = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\userReplay\\"

pathToOtherReplays = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\otherReplays\\"
```

Realistically you can have the replays anywhere on your machine, just change the path!

## How it works/Proof of concept
- This program compares a user's replay with others in order to see how close the cursor movement is to eachother
- The test replays here are Cookiezi's Timefreeze  FC, _Ryuk's FC, and a replay botted copy of Cookiezi's FC
- The distances of the x and y coordinates of each play are compared against each-other
- The average distance of the cursor between the legit and copied Cookiezi play is about 13 pixels
- The average distance of the cursor between the legit _Ryuk play and Cookiezi play is about 156 pixels


## TODO
1. Check for HR plays that were flipped and played No-mod
2. Integrate using the osu! api
   - find an alternative to /api/get_replay as it's rate limited to 10 requests per min
   - once found find an efficient way to download all avaliable replays from that mapset to check against
   - potentially give each replay a unique score based upon average cursor postion to store in a database, that way all replays don't need to be downloaded all the time
3. osu! client integration 
   - Check scores upon score submission
   - Includes a user's previously submitted score(s) on that map. 
