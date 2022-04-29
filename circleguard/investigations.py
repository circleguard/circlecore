from datetime import timedelta

import numpy as np
from scipy import signal
from slider.beatmap import Circle, Slider, Spinner as SliderSpinner

from circleguard.mod import Mod
from circleguard.utils import KEY_MASK
from circleguard import utils
from circleguard.game_version import GameVersion
from circleguard.hitobjects import Hitobject, Spinner
from circleguard.judgment import JudgmentType, Miss, Hit


class Investigations:
    # https://osu.ppy.sh/home/changelog/stable40/20190207.2
    VERSION_SLIDERBUG_FIXED_STABLE = GameVersion(20190207, concrete=True)
    # https://osu.ppy.sh/home/changelog/cuttingedge/20190111
    VERSION_SLIDERBUG_FIXED_CUTTING_EDGE = GameVersion(20190111, concrete=True)

    @staticmethod
    def ur(replay, beatmap, adjusted):
        """
        Calculates the ur of ``replay`` when played against ``beatmap``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to calculate the ur of.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to calculate ``replay``'s ur with.
        adjusted: boolean
            Whether to filter outlier hits before calculating ur.
        """
        # TODO cache hits in replay so we don't recalculate hits for both ur
        # and hits / judgments?
        hits = Investigations.hits(replay, beatmap)
        diffs = [hit.error() for hit in hits]
        if adjusted:
            diffs = utils.filter_outliers(diffs)
        return np.std(diffs) * 10

    @staticmethod
    def snaps(replay, max_angle, min_distance, beatmap):
        """
        Calculates the angle between each set of three points (a,b,c) and finds
        points where this angle is extremely acute and neither ``|ab|`` or
        ``|bc|`` are small.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to investigate for aim correction.
        max_angle: float
            Consider only (a,b,c) where ``∠abc < max_angle``
        min_distance: float
            Consider only (a,b,c) where ``|ab| > min_distance`` and
            ``|bc| > min_distance``.
        beatmap: :class:`slider.beatmap.Beatmap`
            If passed, only the snaps that occur on a hitobject in this beatmap
            will be returned.

        Returns
        -------
        list[:class:`~.Snap`]
            Hits where the angle was less than ``max_angle`` and the distance
            was more than ``min_distance``.

        Notes
        -----
        This does not detect correction where multiple datapoints are placed
        at the correction site (which creates a small ``min_distance``).

        Another possible method is to look at the ratio between the angle
        and distance.
        """
        # when we leave mutliple frames with the same time values, they
        # sometimes get detected (falesly) as aim correction.
        # TODO Worth looking into a bit more to see if we can avoid it without
        # removing the frames entirely.
        t, xy = Investigations.remove_duplicate_t(replay.t, replay.xy)
        t = t[1:-1]

        # label three consecutive points (a b c) and the vectors between them
        # (ab, bc, ac)
        a = xy[:-2]
        b = xy[1:-1]
        c = xy[2:]

        ab = b - a
        bc = c - b
        ac = c - a

        # Distance a to b, b to c, and a to c
        AB = np.linalg.norm(ab, axis=1)
        BC = np.linalg.norm(bc, axis=1)
        AC = np.linalg.norm(ac, axis=1)
        # Law of cosines, solve for beta
        # AC^2 = AB^2 + BC^2 - 2 * AB * BC * cos(beta)
        # cos(beta) = -(AC^2 - AB^2 - BC^2) / (2 * AB * BC)
        num = -(AC ** 2 - AB ** 2 - BC ** 2)
        denom = (2 * AB * BC)
        # use true_divide for handling division by zero
        cos_beta = np.true_divide(num, denom, out=np.full_like(num, np.nan),
            where=denom!=0)
        # rounding issues makes cos_beta go out of arccos' domain, so restrict
        # it
        cos_beta = np.clip(cos_beta, -1, 1)

        beta = np.rad2deg(np.arccos(cos_beta))

        min_AB_BC = np.minimum(AB, BC)
        dist_mask = min_AB_BC > min_distance
        # use less to avoid comparing to nan
        angle_mask = np.less(beta, max_angle, where=~np.isnan(beta))
        # datapoints where both distance and angle requirements are met
        mask = dist_mask & angle_mask

        snaps = []
        for (t, xy, b, d) in zip(t[mask], b[mask], beta[mask], min_AB_BC[mask]):
            # can't discard any snaps if we don't know the beatmap, so count all
            # of them
            if not beatmap:
                snaps.append(Snap(t, b, d))
                continue

            hitobj = beatmap.closest_hitobject(timedelta(milliseconds=int(t)))
            hitobj = Hitobject.from_slider_hitobj(hitobj, replay, beatmap)

            # ignore snaps on spinners
            if isinstance(hitobj, Spinner):
                continue

            easy = Mod.EZ in replay.mods
            hard_rock = Mod.HR in replay.mods
            OD = beatmap.od(easy=easy, hard_rock=hard_rock)

            hitwindow = utils.hitwindow(OD)

            # only count snaps that occur inside hitobjects
            inside_hitobj_pos = np.linalg.norm(xy - hitobj.xy) <= hitobj.radius
            inside_hitobj_t = (hitobj.t - hitwindow) < t < (hitobj.t + hitwindow)
            if inside_hitobj_pos and inside_hitobj_t:
                snaps.append(Snap(t, b, d))

        return snaps

    @staticmethod
    def snaps_sam(replay_data, num_jerks, min_jerk):
        """
        Calculates the jerk at each moment in the Replay, counts the number of
        times it exceeds min_jerk and reports a positive if that number is over
        num_jerks. Also reports all suspicious jerks and their timestamps.

        WARNING
        -------
        Unused function. Kept for historical purposes and ease of viewing in
        case we want to switch to this track of aim correction in the future,
        or provide it as an alternative.
        """

        # get all replay data as an array of type [(t, x, y, k)]
        txyk = np.array(replay_data)

        # drop keypresses
        txy = txyk[:, :3]

        # separate time and space
        t = txy[:, 0]
        xy = txy[:, 1:]

        # j_x = (d/dt)^3 x
        # calculated as (d/dT dT/dt)^3 x = (dT/dt)^3 (d/dT)^3 x
        # (d/dT)^3 x = d(d(dx/dT)/dT)/dT
        # (dT/dt)^3 = 1/(dt/dT)^3
        dtdT = np.diff(t)
        d3xy = np.diff(xy, axis=0, n=3)
        # safely calculate the division and replace with zero if the divisor is
        # zero. dtdT is sliced with 2: because differentiating drops one element
        # for each order (slice (n - 1,) to (n - 3,)).
        # d3xy is of shape (n - 3, 2) so dtdT is also reshaped from (n - 3,) to
        # (n - 3, 1) to align the axes.
        jerk = np.divide(d3xy, dtdT[2:, None] ** 3, out=np.zeros_like(d3xy),
            where=dtdT[2:,None]!=0)

        # take the absolute value of the jerk
        jerk = np.linalg.norm(jerk, axis=1)

        # create a mask of where the jerk reaches suspicious values
        anomalous = jerk > min_jerk
        # and retrieve and store the timestamps and the values themself
        timestamps = t[3:][anomalous]
        values = jerk[anomalous]
        # reshape to an array of type [(t, j)]
        jerks = np.vstack((timestamps, values)).T

        # count the anomalies
        ischeat = anomalous.sum() > num_jerks

        return [jerks, ischeat]

    @staticmethod
    def frametime(replay):
        """
        Calculates the median time between the frames of ``replay``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to calculate the frametime of.

        Notes
        -----
        Median is used instead of mean to lessen the effect of outliers.
        """
        frametimes = Investigations.frametimes(replay)
        return np.median(frametimes)

    @staticmethod
    def frametimes(replay):
        """
        Returns the time between each two consecutive frames in ``replay``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to get the frametimes of.
        """
        return np.diff(replay.t)

    @staticmethod
    def keydown_frames(replay):
        """
        Get the frames of ``replay`` which had a keydown event, and we should
        consider eligible to hit a hitobject.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to get the keydown frames of.

        Returns
        -------
        ndarray(float, [float, float])
            The keydown frames for the replay. The first float is the time of
            that frame, the second and third floats are the x and y position
            of the cursor at that frame.
        """
        keydown_frames = []

        # the keydowns for each frame. Frames are "keydown" frames if an
        # additional key was pressed from the previous frame. If keys pressed
        # remained the same or decreased (a key previously pressed is no longer
        # pressed) from the previous frame, ``keydowns`` is zero for that frame.
        keydowns = replay.keydowns

        for i, keydown in enumerate(keydowns):
            if keydown != 0:
                keydown_frames.append([replay.t[i], replay.xy[i]])

        # add a duplicate frame when 2 keys are pressed at the same time
        keydowns = keydowns[keydowns != 0]
        i = 0
        for j in np.where(keydowns == KEY_MASK)[0]:
            keydown_frames.insert(j + i + 1, keydown_frames[j + i])
            i += 1

        return keydown_frames

    @staticmethod
    def hits(replay, beatmap):
        judgment = Investigations.judgments(replay, beatmap)
        judgments = [j for j in judgment if isinstance(j, Hit)]
        return judgments

    # TODO add exception for 2b objects (>1 object at the same time) for current
    # version of notelock
    @staticmethod
    def judgments(replay, beatmap):
        """
        Determines the judgments (where hitobjs were hit or missed, and if hit
        then what type of hit - a 300, 100, or 50) of the given ``replay``
        played against the given ``beatmap``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to determine the judgments of when played against
            ``beatmap``.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to determine the udgments of when ``replay`` is played
            against it.
        """
        game_version = replay.game_version

        if not game_version.available():
            # if we have no information about the version, assume it was played
            # after sliderbug was fixed.
            sliderbug_fixed = True

        if not game_version.concrete:
            # if we're only estimating the version, assume the replay was played
            # on stable. if we used the cutting edge version instead, we would
            # be incorrectly using logic for sliderbug being fixed for all
            # replays between the cutting edge version and the stable version
            # which were played on stable.
            # This is wrong for cutting edge replays between those two versions
            # which do not have a concrete version, but that's better than being
            # wrong for stable replays between those two versions.
            sliderbug_fixed = game_version >= Investigations.VERSION_SLIDERBUG_FIXED_STABLE
        else:
            sliderbug_fixed = game_version >= Investigations.VERSION_SLIDERBUG_FIXED_CUTTING_EDGE

        easy = Mod.EZ in replay.mods
        hard_rock = Mod.HR in replay.mods
        hitobjs = beatmap.hit_objects(easy=easy, hard_rock=hard_rock)

        OD = beatmap.od(easy=easy, hard_rock=hard_rock)
        CS = beatmap.cs(easy=easy, hard_rock=hard_rock)
        keydowns = Investigations.keydown_frames(replay)

        judgments = []

        (hw_50, hw_100, hw_300) = utils.hitwindows(OD)
        hitradius = utils.hitradius(CS)

        # keep track of the indices of which hitobjs have been hit so far (none
        # have been hit to start). At the end we'll look through this array and
        # if any index is still ``False``, we'll mark that as a miss.
        hitobj_hit = np.zeros(len(hitobjs), dtype=bool)

        hitobj_i = 0
        keydown_i = 0

        while hitobj_i < len(hitobjs) and keydown_i < len(keydowns):
            hitobj = hitobjs[hitobj_i]
            hitobj_t = hitobj.time.total_seconds() * 1000
            hitobj_xy = [hitobj.position.x, hitobj.position.y]

            keydown_t = keydowns[keydown_i][0]
            keydown_xy = keydowns[keydown_i][1]

            if isinstance(hitobj, Circle):
                hitobj_type = 0
                hitobj_end_time = hitobj_t + hw_50
            elif isinstance(hitobj, Slider):
                hitobj_type = 1
                hitobj_end_time = hitobj.end_time.total_seconds() * 1000
            else:
                hitobj_type = 2
                hitobj_end_time = hitobj.end_time.total_seconds() * 1000

            # before sliderbug fix, notelock ended after hitwindow50
            if not sliderbug_fixed:
                notelock_end_time = hitobj_t + hw_50
                # exception for sliders/spinners, where notelock ends after
                # hitobject end time if it's earlier
                if hitobj_type != 0:
                    notelock_end_time = min(notelock_end_time, hitobj_end_time)
            # after sliderbug fix, notelock ends after hitobject end time
            else:
                notelock_end_time = hitobj_end_time
                # apparently notelock was increased by 1ms for circles
                # (from testing)
                if hitobj_type == 0:
                    notelock_end_time += 1


            # can't press on hitobjects before hitwindowmiss
            if keydown_t < hitobj_t - 400:
                keydown_i += 1
                continue

            if keydown_t <= hitobj_t - hw_50:
                # pressing on a circle or slider during hitwindowmiss will cause
                # a miss
                if np.linalg.norm(keydown_xy - hitobj_xy) <= hitradius and hitobj_type != 2:
                    # sliders don't disappear after missing
                    # so we skip to the press_i that is after notelock_end_time
                    if hitobj_type == 1 and sliderbug_fixed:
                        while keydowns[keydown_i][0] < notelock_end_time:
                            keydown_i += 1
                            if keydown_i >= len(keydowns):
                                break
                    else:
                        keydown_i += 1
                    hitobj_i += 1
                # keypress not on object, so we move to the next keypress
                else:
                    keydown_i += 1
            elif keydown_t >= notelock_end_time:
                # can no longer interact with hitobject after notelock_end_time
                # so we move to the next object
                hitobj_i += 1
            else:
                if (keydown_t < hitobj_t + hw_50 and
                    np.linalg.norm(keydown_xy - hitobj_xy) <= hitradius and
                    hitobj_type != 2):

                    # sliderheads are always 300s even if you click early or
                    # late
                    if hitobj_type == 1:
                        hit_type = JudgmentType.Hit300
                    # TODO: should these ranges be inclusive?
                    elif abs(keydown_t - hitobj_t) < hw_300:
                        hit_type = JudgmentType.Hit300
                    elif abs(keydown_t - hitobj_t) < hw_100:
                        hit_type = JudgmentType.Hit100
                    elif abs(keydown_t - hitobj_t) < hw_50:
                        hit_type = JudgmentType.Hit50

                    judgment = Hit(hitobj, keydown_t, keydown_xy,
                        replay, beatmap, hit_type)
                    judgments.append(judgment)
                    hitobj_hit[hitobj_i] = True

                    # sliders don't disappear after clicking
                    # so we skip to the press_i that is after notelock_end_time
                    if hitobj_type == 1 and sliderbug_fixed:
                        while keydowns[keydown_i][0] < notelock_end_time:
                            keydown_i += 1
                            if keydown_i >= len(keydowns):
                                break
                    else:
                        keydown_i += 1
                    hitobj_i += 1
                # keypress not on object, so we move to the next keypress
                else:
                    keydown_i += 1

        # add a Miss for each hitobj that was never hit
        for i, hitobj_hit_ in enumerate(hitobj_hit):
            # ignore if the hitobj is a spinner, we don't calculate judgments
            # for spinners yet
            if not hitobj_hit_ and not isinstance(hitobjs[i], SliderSpinner):
                judgment = Miss(hitobjs[i], replay, beatmap)
                judgments.append(judgment)

        return judgments

    @staticmethod
    def similarity(replay1, replay2, method, num_chunks, mods_unknown):
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
        t1, xy1 = Investigations.remove_duplicate_t(replay1.t, replay1.xy)
        t2, xy2 = Investigations.remove_duplicate_t(replay2.t, replay2.xy)
        xy1, xy2 = Investigations.interpolate(t1, t2, xy1, xy2)
        xy1, xy2 = Investigations.clean(xy1, xy2)

        # kind of a dirty function with all the switching between similarity
        # and correlation, but I'm not sure I can make it any cleaner

        if not replay1.mods or not replay2.mods:
            # first compute with no modifications
            if method == "similarity":
                sim1 = Investigations.compute_similarity(xy1, xy2)
            if method == "correlation":
                sim1 = Investigations.compute_correlation(xy1, xy2, num_chunks)

            # then compute with hr applied to ``replay1``
            xy1[:, 1] = 384 - xy1[:, 1]

            if method == "similarity":
                sim2 = Investigations.compute_similarity(xy1, xy2)
            if method == "correlation":
                sim2 = Investigations.compute_correlation(xy1, xy2, num_chunks)

            if mods_unknown == "best":
                if method == "similarity":
                    return min(sim1, sim2)
                if method == "correlation":
                    return max(sim1, sim2)

            if mods_unknown == "both":
                return (sim1, sim2)

        # flip if one but not both has HR
        if (Mod.HR in replay1.mods) ^ (Mod.HR in replay2.mods):
            xy1[:, 1] = 384 - xy1[:, 1]

        if method == "similarity":
            return Investigations.compute_similarity(xy1, xy2)
        if method == "correlation":
            return Investigations.compute_correlation(xy1, xy2, num_chunks)

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
        The length of the two returned arrays will be equal. This is a
        (desirous) side effect of interpolating.
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


class Snap:
    """
    A suspicious hit in a replay, specifically so because it snaps away from
    the otherwise normal path. Snaps represent the middle frame in a set of
    three replay frames (so for example ``time`` is the time of the middle
    frame).

    Parameters
    ----------
    time: int
        The time value of the middle datapoint, in ms. 0 represents the
        beginning of the replay.
    angle: float
        The angle between the three datapoints.
    distance: float
        ``min(dist_a_b, dist_b_c)`` if ``a``, ``b``, and ``c`` are three
        datapoints with ``b`` being the middle one.
    """
    def __init__(self, time, angle, distance):
        self.time = time
        self.angle = angle
        self.distance = distance

    def __eq__(self, other):
        return (self.time == other.time and self.angle == other.angle
                and self.distance == other.distance)

    def __hash__(self):
        return hash((self.time, self.angle, self.distance))
