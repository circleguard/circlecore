import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("-m", "--map", dest="map_id",
                    help="checks the leaderboard on the given beatmap id against each other")

argparser.add_argument("-u", "--user", dest="user_id",
                    help="checks only the given user against the other leaderboard replays. Must be set with -m")

argparser.add_argument("-l", "--local", help=("compare scores under the user/ directory to a beatmap leaderboard (if set with -m), "
                                             "a score set by a user on a beatmap (if set with -m and -u) or other locally "
                                            "saved replays (default behavior)"), action="store_true")

argparser.add_argument("-t", "--threshold", help="sets the similarity threshold to print results that score under it. Defaults to 20", type=int, default=20)

argparser.add_argument("-n", "--number", help="how many replays to get from a beatmap. No effect if not set with -m. Must be between 1 and 100 inclusive,"
                                              "defaults to 50. NOTE: THE TIME COMPLEXITY OF THE COMPARISONS WILL SCALE WITH O(n^2).", type=int, default=50)

argparser.add_argument("-c", "--cache", help="If set, locally caches replays so they don't have to be redownloaded when checking the same map multiple times.",
                                        action="store_true")

argparser.add_argument("-s", "--single", help="Compare all replays under user/ with all other replays under user/. No effect if not set with -l",
                                        action="store_true")
