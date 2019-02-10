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
    
    def __init__(self, loader, user_id, threshold, silent, stddevs=None):
        """
        Initializes a Screener instance.

        Args:
            Loader loader: The loader all api requests are handled with.
            Integer user_id: The user to screen.
            Integer threshold: See Comparer
            Boolean silent: See Comparer
            Float stddev: See Comparer
        """
        
        self.loader = loader
        self.user_id = user_id
        self.threshold = threshold
        self.silent = silent
        self.stddevs = stddevs

    def screen(self):
        """
        Starts the screening.
        """

        best = self.loader.get_user_best(self.user_id)

        for performance in best:
            map_id = performance['beatmap_id']

            #load user and check replays here, then make Comparer and run.

        
