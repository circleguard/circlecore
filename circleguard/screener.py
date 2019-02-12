from comparer import Comparer

class Screener:
    """
    A class for screening a user's top plays

    Attributes:
        Loader loader: The loader all api requests are handled with.
        Integer user_id: The user to screen.
        Integer threshold: If a comparison scores below this value, the result is printed.
        Boolean silent: If true, visualization prompts will be ignored and only results will be printed.
        Float stddevs: If set, the threshold will be automatically set to this many standard deviations below the average similarity for the comparisons.

    See Also:
        Comparer
    """

    def __init__(self, cacher, loader, threshold, silent, user_id, number, stddevs):
        """
        Initializes a Screener instance.

        Args:
            Cacher cacher: The cacher cached replays are loaded from.
            Loader loader: The loader all api requests are handled with.
            Integer threshold: If a comparison scores below this value, the result is not printed.
            Boolean silent: If true, visualization prompts will be ignored and only results will be printed.
            Integer user_id: The user id to check the top plays of.
            Integer number: The number of top plays on each map to compare against the user's play on that map.
            Float stddevs: If not None, the threshold will be automatically set to this many standard deviations below the average similarity each set of comparisons.
        """

        self.cacher = cacher
        self.loader = loader
        self.threshold = threshold
        self.silent = silent
        self.user_id = user_id
        self.number = number
        self.stddevs = stddevs

    def screen(self):
        """
        Starts the screening.
        """


        print(f"Screening user {self.user_id}")

        best = self.loader.get_user_best(self.user_id, self.number)
        map_ids = [play['beatmap_id'] for play in best]
        for i, map_id in enumerate(map_ids, 1):

            print(f"Screening on map {map_id}, {i}/{len(best)}")

            # load screened player
            user_info = self.loader.user_info(map_id, self.user_id)[self.user_id]

            if(user_info[3] == 0): #replay unavailable, check before we waste a heavy api call
                print("replay unavailable for screened user, skipping map {}".format(map_id))
                continue

            replays_check = [self.loader.replay_from_map(self.cacher, map_id, self.user_id, user_info[0], user_info[1], user_info[2])]

            # load other players on map
            users_info = self.loader.users_info(map_id, self.number)
            replays2 = self.loader.replay_from_user_info(self.cacher, map_id, users_info)

            comparer = Comparer(self.threshold, self.silent, replays_check, replays2=replays2, stddevs=self.stddevs)
            comparer.compare(mode="double")

            self.loader.reset()

        print("Finished screening")
