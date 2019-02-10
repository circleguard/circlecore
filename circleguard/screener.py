from comparer import Comparer

class Screener:
    """
    A class for screening a single player's history.

    Attributes:
        Loader loader: The loader all api requests are handled with.
        Integer user_id: The user to screen.
        Integer threshold: See Comparer
        Boolean silent: See Comparer
        Float stddev: See Comparer

    See Also:
        Comparer
    """
    
    def __init__(self, cacher, loader, args):
        """
        Initializes a Screener instance.

        Args:
            Cacher cacher: The cacher cached replays are loaded from.
            Loader loader: The loader all api requests are handled with.
            Args args: The arguments to run the screening with.
        """

        self.cacher = cacher
        self.loader = loader
        self.args = args

    def screen(self):
        """
        Starts the screening.
        """

        args = self.args

        print(f"Screening user {args.user_id}")

        best = self.loader.get_user_best(args.user_id)

        for i, performance in enumerate(best, 1):
            map_id = performance['beatmap_id']
            print(f"Screening on map {map_id}, {i}/{len(best)}")

            # load screened player
            user_info = self.loader.user_info(map_id, args.user_id)[args.user_id]
            replays_check = [self.loader.replay_from_map(self.cacher, map_id, args.user_id, user_info[0], user_info[1], user_info[2])]        

            # load other players on map
            users_info = self.loader.users_info(map_id, args.number)
            replays2 = self.loader.replay_from_user_info(self.cacher, map_id, users_info)
            
            comparer = Comparer(args.threshold, args.silent, replays_check, replays2=replays2, stddevs=args.stddevs)
            comparer.compare(mode="double")

        print("Finished screening")
