import itertools
import sys

import numpy as np
import math

from circleguard.draw import Draw
from circleguard.replay import Replay
from circleguard.enums import Mod
from circleguard.exceptions import InvalidArgumentsException, CircleguardException
import circleguard.utils as utils
from circleguard.result import Result
import circleguard.config as config

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

    def __init__(self, threshold, silent, replays1, replays2=None):
        """
        Initializes a Comparer instance.

        Note that the order of the two replay lists has no effect; they are only numbered for consistency.
        Comparing 1 to 2 is the same as comparing 2 to 1.

        Args:
            Integer threshold: If a comparison scores below this value, the result is printed.
            Boolean silent: If true, visualization prompts will be ignored and only results will be printed.
            List replays1: A list of Replay instances to compare against replays2.
            List replays2: A list of Replay instances to be compared against. Optional, defaulting to None. No attempt to error check
                           this is made - if a compare(mode="double") call is made, the program will throw an AttributeError. Be sure to only call
                           methods that involve the first set of replays.
            Float stddevs: If set, the threshold will be automatically set to this many standard deviations below the average similarity for the comparisons.
        """

        self.threshold = threshold

        # filter beatmaps we had no data for - see Loader.replay_data and OnlineReplay.from_map
        self.replays1 = [replay for replay in replays1 if replay.replay_data is not None]
        self.replays2 = [replay for replay in replays2 if replay.replay_data is not None] if replays2 else None

    def compare(self, mode):
        """
        If mode is "double", compares all replays in replays1 against all replays in replays2.
        If mode is "single", compares all replays in replays1 against all other replays in replays1 (len(replays1) choose 2 comparisons).
        In both cases, prints the result of each comparison according to _print_result.

        Args:
            String mode: One of either "double" or "single", determining how to choose which replays to compare.
        """

        if(not self.replays1 or not self.replays2): # if either are empty, bad things
            if(config.failfast):
                raise CircleguardException("No comparisons could be made from the given replays")
            else:
                return

        if(mode == "double"):
            iterator = itertools.product(self.replays1, self.replays2)
        elif (mode == "single"):
            iterator = itertools.combinations(self.replays1, 2)
        else:
            raise InvalidArgumentsException("'mode' must be one of 'double' or 'single'")

        for replay1, replay2 in iterator:
            yield from self.determine_result(replay1, replay2)


    def determine_result(self, replay1, replay2):
        """
        Prints a human readable version of the result if the average distance
        is below the threshold set from the command line.

        Args:
            Tuple result: A tuple containing (average distance, standard deviation) of a comparison.
            Replay replay1: The replay to print the name of and to draw against replay2
            Replay replay2: The replay to print the name of and to draw against replay1
        """
        result = Comparer._compare_two_replays(replay1, replay2)
        mean = result[0]
        sigma = result[1]
        ischeat = False
        if(mean < self.threshold):
            ischeat = True

        # if they were both set locally, we may not get replay ids to compare
        later_name = None
        if(replay1.replay_id and replay2.replay_id):
            later_name = replay1.username if(replay1.replay_id > replay2.replay_id) else replay2.username
        yield Result(replay1, replay2, mean, ischeat, later_name)

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
        (data1, data2) = utils.interpolate(data1, data2)

        # remove time from each tuple
        data1 = [d[1:] for d in data1]
        data2 = [d[1:] for d in data2]

        mods1 = replay1.mods
        mods2 = replay2.mods
        if(type(replay1.mods) is not frozenset):
            mods1 = frozenset(Mod(mod_val) for mod_val in utils.bits(replay1.mods)) # TODO deal with frozenset being ugly and replicated here
        if(type(replay2.mods) is not frozenset):
            mods2 = frozenset(Mod(mod_val) for mod_val in utils.bits(replay2.mods))
        flip1 = Mod.HardRock.value in [mod.value for mod in mods1]
        flip2 = Mod.HardRock.value in [mod.value for mod in mods2]
        if(flip1 ^ flip2): # xor, if one has hr but not the other
            for d in data1:
                d[1] = 384 - d[1]

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
