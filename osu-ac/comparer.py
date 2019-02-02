import itertools

import numpy as np

from draw import Draw
from replay import Replay
from config import WHITELIST

class Comparer:
    """
    A class for managing a set of replay comparisons.

    Attributes:
        List replays1: A list of Replay instances to compare against replays2.
        List replays2: A list of Replay instances to be compared against. Optional, defaulting to None. No attempt to error check
                       this is made - if a compare() call is made, the program will throw an AttributeError. Be sure to only call
                       methods that involve the first set of replays if this argument is not passed.
        Integer threshold: If a comparison scores below this value, the result is printed.

    See Also:
        Investigator
    """

    def __init__(self, threshold, silent, replays1, replays2=None, stddevs=None):
        """
        Initializes a Comparer instance.

        Note that the order of the two replay lists has no effect; they are only numbered for consistency.
        Comparing 1 to 2 is the same as comparing 2 to 1.

        Args:
            Integer threshold: If a comparison scores below this value, the result is printed.
            Boolean silent: If true, visualization prompts will be ignored and only results will be printed.
            List replays1: A list of Replay instances to compare against replays2.
            List replays2: A list of Replay instances to be compared against. Optional, defaulting to None. No attempt to error check
                           this is made - if a compare() call is made, the program will throw an AttributeError. Be sure to only call
                           methods that involve the first set of replays.
            Float stddevs: If set, the threshold will be automatically set to this many standard deviations below the average similarity for the comparisons.
        """

        self.threshold = threshold
        self.stddevs = stddevs
        self.silent = silent

        # filter beatmaps we had no data for - see Loader.replay_data and OnlineReplay.from_map
        self.replays1 = [replay for replay in replays1 if replay is not None]

        if(replays2):
            self.replays2 = [replay for replay in replays2 if replay is not None]

    def compare(self, mode):
        """
        If mode is "double", compares all replays in replays1 against all replays in replays2.
        If mode is "single", compares all replays in replays1 against all other replays in replays1 (len(replays1) choose 2 comparisons).
        In both cases, prints the result of each comparison according to _print_result.

        Args:
            String mode: One of either "double" or "single", determining how to choose which replays to compare.
        """

        if(not self.replays1): # if this is empty, bad things
            print("No comparisons could be made. Make sure replay data is available for your args")
            return

        if(mode == "double"):
            iterator = itertools.product(self.replays1, self.replays2)
        elif (mode == "single"):
            iterator = itertools.combinations(self.replays1, 2)
        else:
            raise Exception("`mode` must be one of 'double' or 'single'")

        print("Starting to compare replays")
        # automatically determine threshold based on standard deviations of similarities if stddevs is set
        if(self.stddevs):
            results = {}
            for replay1, replay2 in iterator:
                if(self.check_names(replay1.player_name, replay2.player_name)):
                    continue
                result = Comparer._compare_two_replays(replay1, replay2)
                results[(replay1, replay2)] = result

            similarities = [result[0] for result in results.values()]

            mu, sigma = np.mean(similarities), np.std(similarities)

            self.threshold = mu - self.stddevs * sigma
            print("\n\nAutomatically determined threshold limit: {:.1f}\nAverage similarity: {:.1f}".format(self.threshold, mu))
            print(f"Standard deviation of similarities: {sigma:.2f}, {'in' if sigma / mu < 0.2 else ''}significant\n\n")

            for key in results:
                self._print_result(results[key], key[0], key[1])
        # else print normally
        else:
            for replay1, replay2 in iterator:
                if(self.check_names(replay1.player_name, replay2.player_name)):
                    continue
                result = Comparer._compare_two_replays(replay1, replay2)
                self._print_result(result, replay1, replay2)



        print("done comparing")

    def check_names(self, player1, player2):
        """
        Returns True if both players are in the whitelist or are the same name, False otherwise.

        Args:
            String player1: The name of the first player.
            String player2: The name of the second player.
        """

        return ((player1 in WHITELIST and player2 in WHITELIST) or (player1 == player2))

    def _print_result(self, result, replay1, replay2):
        """
        Prints a human readable version of the result if the average distance
        is below the threshold set from the command line.

        Args:
            Tuple result: A tuple containing (average distance, standard deviation) of a comparison.
            Replay replay1: The replay to print the name of and to draw against replay2
            Replay replay2: The replay to print the name of and to draw against replay1
        """

        mean = result[0]
        sigma = result[1]

        if(mean > self.threshold):
            return

        # if they were both set locally, we don't get replay ids to compare
        last_score = None
        if(replay1.replay_id and replay2.replay_id):
            last_score = replay1.player_name if(replay1.replay_id > replay2.replay_id) else replay2.player_name

        print("{:.1f} similarity, {:.1f} std deviation ({} vs {}{})"
              .format(mean, sigma, replay1.player_name, replay2.player_name, " - {} set later".format(last_score) if last_score else ""))

        if(self.silent):
            return
        import sys
        print("Would you like to see a visualization of both replays?")
        answer = sys.stdin.readline()
        if (answer and answer[0].lower().strip() == "y"):
            draw = Draw(replay1, replay2)
            animation = draw.run()

    @staticmethod
    def _compare_two_replays(replay1, replay2):
        """
        Compares two Replays and return their average distance
        and standard deviation of distances.
        """

        # get all coordinates in numpy arrays so that they're arranged like:
        # [ x_1 x_2 ... x_n
        #   y_1 y_2 ... y_n ]
        # indexed by columns first.
        data1 = replay1.as_list_with_timestamps()
        data2 = replay2.as_list_with_timestamps()

        # interpolate
        (data1, data2) = Replay.interpolate(data1, data2)

        # remove time from each tuple
        data1 = [d[1:] for d in data1]
        data2 = [d[1:] for d in data2]

        (mu, sigma) = Comparer._compute_data_similarity(data1, data2)

        return (mu, sigma)

    @staticmethod
    def _compute_data_similarity(data1, data2):
        """
        Finds the similarity and standard deviation between two datasets.

        Args:
            List data1: A list of tuples containing the (x, y) coordinate of points
            List data2: A list of tuples containing the (x, y) coordinate of points

        Returns:
            A tuple containing (similarity value, standard deviation) between the two datasets
        """

        data1 = np.array(data1)
        data2 = np.array(data2)

        # switch if the second is longer, so that data1 is always the longest.
        if len(data2) > len(data1):
            (data1, data2) = (data2, data1)

        shortest = len(data2)

        distance = data1[:shortest] - data2
        # square all numbers and sum over the second axis (add row 2 to row 1),
        # finally take the square root of each number to get all distances.
        # [ x_1 x_2 ... x_n   => [ x_1 ** 2 ... x_n ** 2
        #   y_1 y_2 ... y_n ] =>   y_1 ** 2 ... y_n ** 2 ]
        # => [ x_1 ** 2 + y_1 ** 2 ... x_n ** 2 + y_n ** 2 ]
        # => [ d_1 ... d_2 ]
        distance = (distance ** 2).sum(axis=1) ** 0.5

        mu, sigma = distance.mean(), distance.std()

        return (mu, sigma)
