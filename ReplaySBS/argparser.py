import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("-m", "--map", dest="map_id",
                    help="checks the top 50 replays on the given beatmap id against each other (50choose2 = 1250 operations)")

argparser.add_argument("-u", "--user", dest="user_id",
                    help="checks only the given user against the other top 50 replays. Must be set with --map (49 operations)")
