import numpy as np
from scipy import signal

from circleguard.mod import Mod

class Comparer:

    @staticmethod
    def similarity(replay1, replay2, method, num_chunks, mods_unknown_behavior):
        """
        Compares two :class:`~.replay.Replay`\s.

        Parameters
        ----------
        replay1: :class:`~.replay.Replay`
            The first replay to compare.
        replay2: :class:`~.replay.Replay`
            The second replay to compare.

        Returns
        -------
        :class:`~.result.ComparisonResult`
            The result of comparing ``replay1`` to ``replay2``.
        """
        # perform preprocessing here as an optimization, so it is not repeated
        # within different comparison algorithms. This will likely need to
        # become more advanced if we add more (and different) algorithms.

        # interpolation breaks when multiple frames have the same time values
        # (which occurs semi frequently in replays). So filter them out
        t1, xy1 = Comparer.remove_duplicate_t(replay1.t, replay1.xy)
        t2, xy2 = Comparer.remove_duplicate_t(replay2.t, replay2.xy)
        xy1, xy2 = Comparer.interpolate(t1, t2, xy1, xy2)
        xy1, xy2 = Comparer.clean(xy1, xy2)

        # kind of a dirty function with all the switching between similarity
        # and correlation, but I'm not sure I can make it any cleaner

        if not replay1.mods or not replay2.mods:
            # first compute with no modifications
            if method == "similarity":
                sim1 = Comparer.compute_similarity(xy1, xy2)
            if method == "correlation":
                sim1 = Comparer.compute_correlation(xy1, xy2, num_chunks)

            # then compute with hr applied to ``replay1``
            xy1[:, 1] = 384 - xy1[:, 1]

            if method == "similarity":
                sim2 = Comparer.compute_similarity(xy1, xy2)
            if method == "correlation":
                sim2 = Comparer.compute_correlation(xy1, xy2, num_chunks)

            if mods_unknown_behavior == "best":
                if method == "similarity":
                    return min(sim1, sim2)
                if method == "correlation":
                    return max(sim1, sim2)

            if mods_unknown_behavior == "both":
                return (sim1, sim2)

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        if method == "similarity":
            return Comparer.compute_similarity(xy1, xy2)
        if method == "correlation":
            return Comparer.compute_correlation(xy1, xy2, num_chunks)


    @staticmethod
    def compute_similarity(xy1, xy2):
        """
        Calculates the average distance between two sets of cursor position
        data.

        Parameters
        ----------
        replay1: ndarray
            The first xy data to compare.
        replay2: ndarray
            The second xy data to compare.

        Returns
        -------
        float
            The mean distance between the two datasets.
        """

        # euclidean distance
        distance = xy1 - xy2
        distance = (distance ** 2).sum(axis=1) ** 0.5
        return distance.mean()


    @staticmethod
    def compute_correlation(xy1, xy2, num_chunks):

        xy1 = xy1.T
        xy2 = xy2.T

        # section into chunks, used to reduce the effect of outlier data
        # (eg. cheater inserts replay data during breaks that places them
        # far away from the actual replay)
        horizontal_length = xy1.shape[1] - xy1.shape[1] % num_chunks
        xy1_parts = np.hsplit(xy1[:,:horizontal_length], num_chunks)
        xy2_parts = np.hsplit(xy2[:,:horizontal_length], num_chunks)
        correlations = []
        for (xy1_part, xy2_part) in zip(xy1_parts, xy2_parts):
            xy1_part -= np.mean(xy1_part)
            xy2_part -= np.mean(xy2_part)
            norm = np.std(xy1_part) * np.std(xy2_part) * xy1_part.size
            # matrix of correlations between xy1 and xy2 at different time
            # shifts
            cross_corr_matrix = signal.correlate(xy1_part, xy2_part) / norm

            # pick the maximum correlation, which will probably be at 0
            # time shift, unless the replays have been intentionally shifted in
            # time
            max_corr = np.max(cross_corr_matrix)
            correlations.append(max_corr)
        # take the median of all the chunks to reduce the effect of outliers
        return np.median(correlations)


    @staticmethod
    def remove_duplicate_t(t, data):
        t, t_sort = np.unique(t, return_index=True)
        data = data[t_sort]
        return (t, data)


    @staticmethod
    def interpolate(t1, t2, xy1, xy2):
        """
        Interpolates the xy data of the shorter replay to the longer replay.

        Returns
        -------
        (ndarray, ndarray)
            The interpolated replay data of the first and second replay
            respectively.

        Notes
        -----
        The length of the two returned arrays will be equal. This is a (desired)
        side effect of interpolating.
        """

        if len(t1) > len(t2):
            xy2x = np.interp(t1, t2, xy2[:, 0])
            xy2y = np.interp(t1, t2, xy2[:, 1])
            xy2 = np.array([xy2x, xy2y]).T
        else:
            xy1x = np.interp(t2, t1, xy1[:, 0])
            xy1y = np.interp(t2, t1, xy1[:, 1])
            xy1 = np.array([xy1x, xy1y]).T

        return (xy1, xy2)


    @staticmethod
    def clean(xy1, xy2):
        """
        Cleans the given xy data to only include indices where both coordinates
        are inside the osu gameplay window (a 512 by 384 osu!pixel window).

        Warnings
        --------
        The length of the two passed arrays must be equal.
        """

        valid = np.all(([0, 0] <= xy1) & (xy1 <= [512, 384]), axis=1) & \
            np.all(([0, 0] <= xy2) & (xy2 <= [512, 384]), axis=1)
        xy1 = xy1[valid]
        xy2 = xy2[valid]
        return (xy1, xy2)
