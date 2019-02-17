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


        print(f"Screening user {self.user_id}. Replays may appear to be downloaded multiple times for some maps - this is to check for play remodding.")

        best = self.loader.get_user_best(self.user_id, self.number)
        map_ids = [play['beatmap_id'] for play in best]
        for i, map_id in enumerate(map_ids, 1):

            print(f"Screening on map {map_id} (map {i}/{len(best)})")

            # load screened player
            user_info = self.loader.user_info(map_id, self.user_id, limit=False)

            if(user_info[0][3] == 0): # first replay unavailable (so all subsequent ones are as well), check before we waste a heavy api call
                print("replay unavailable for screened user, skipping map {}".format(map_id))
                continue

            all_replays = self.loader.replay_from_user_info(self.cacher, map_id, user_info)
             # TODO move "replay unavailable so don't load" logic to replay_from_user_info, will mean standardizing
             # loader#users_info to return replay available as well

            # load other players on map
            other_users_info = self.loader.users_info(map_id, self.number)
            # filter out their own replay (happens if they're in the top self.number of that beatmap)
            other_users_info = [info for info in other_users_info if info[0] != self.user_id]

            replays2 = self.loader.replay_from_user_info(self.cacher, map_id, other_users_info)

            # only compare the first replay for replay stealing, highly unlikely they would steal a lower placed replay
            # TODO make a deep investigate compare all?
            comparer = Comparer(self.threshold, self.silent, [all_replays[0]], replays2=replays2, stddevs=self.stddevs)
            comparer.compare(mode="double")

            print("checking for remodding")
            # now compare all their replays against each other for replay remodding
            comparer = Comparer(self.threshold, self.silent, all_replays, stddevs=self.stddevs)
            comparer.compare(mode="single")

            self.loader.reset()

        print("Finished screening")
