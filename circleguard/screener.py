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

        best = self.loader.get_user_best(self.user_id, self.number)
        self.map_ids = [play['beatmap_id'] for play in best]

    def screen(self):
        """
        Starts the screening.
        """

        print("Screening user {}".format(self.user_id))
        self._screen_steal()
        self._screen_remodding()
        print("Finished screening.")


    def _screen_steal(self):
        """
        Checks the top plays of the user for replay stealing
        """

        print("checking for replay stealing")

        for i, map_id in enumerate(self.map_ids, 1):

            print(f"Screening on map {map_id} (map {i}/{len(self.map_ids)})")
            self.loader.new_session(self.number)
            # load screened player
            user_info = self.loader.user_info(map_id, self.user_id)

            replays1 = self.loader.replay_from_user_info(self.cacher, map_id, user_info)
            if(replays1[0] is None): #should only be one replay in replays1 because loader#user_info guarantees it when limit is True
                print("replay unavailable for screened user, skipping map {}".format(map_id))
                continue

            # load other players on map
            other_users_info = self.loader.users_info(map_id, self.number)
            # filter out screened user's own info so we don't duplicate their replay (happens if they're in the top self.number of that beatmap)
            other_users_info = [info for info in other_users_info if info[0] != self.user_id]

            replays2 = self.loader.replay_from_user_info(self.cacher, map_id, other_users_info)

            # only compare the first replay for replay stealing, highly unlikely they would steal a lower placed replay
            # TODO make a deep investigate compare all?
            comparer = Comparer(self.threshold, self.silent, replays1, replays2=replays2, stddevs=self.stddevs)
            comparer.compare(mode="double")

    def _screen_remodding(self):
        """
        Checks the top plays of the user for remodding
        (taking a replay and resubmitting it with different mods, typically for more pp or score)
        """

        print("checking for remodding. The same replay may appear to be downloaded multiple times for some maps - don't worry, they have different mods.")
        for i, map_id in enumerate(self.map_ids, 1):
            print(f"Screening on map {map_id} (map {i}/{len(self.map_ids)})")
            user_info = self.loader.user_info(map_id, self.user_id, limit=False)
            self.loader.new_session(len(user_info))
            replays1 = self.loader.replay_from_user_info(self.cacher, map_id, user_info)
            comparer = Comparer(self.threshold, self.silent, replays1, stddevs=self.stddevs)
            comparer.compare(mode="single")
