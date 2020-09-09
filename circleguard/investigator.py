import numpy as np
from slider.beatmap import Circle, Slider

from circleguard.mod import Mod
from circleguard.utils import KEY_MASK
from circleguard.game_version import GameVersion

class Investigator:
    # https://osu.ppy.sh/home/changelog/stable40/20190207.2
    VERSION_SLIDERBUG_FIXED_STABLE = GameVersion(20190207, concrete=True)
    # https://osu.ppy.sh/home/changelog/cuttingedge/20190111
    VERSION_SLIDERBUG_FIXED_CUTTING_EDGE = GameVersion(20190111, concrete=True)

    @staticmethod
    def ur(replay, beatmap):
        """
        Calculates the ur of ``replay`` when played against ``beatmap``.

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to calculate the ur of.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to calculate ``replay``'s ur with.
        """

        hits = Investigator.hits(replay, beatmap)

        diffs = []
        for hit in hits:
            hitobject_t = hit.hitobject.time.total_seconds() * 1000
            hit_time = hit.t
            diffs.append(hit_time - hitobject_t)
        return np.std(diffs) * 10

    @staticmethod
    def snaps_cross(replay):
        """
        An alternative snap detection algorithm using relative cross products
        of vectors.
        """
        t, xy = Investigator.remove_duplicate_t(replay.t, replay.xy)
        # label three consecutive points (a, b, c) and the vectors between them
        # (ab, bc, ac)
        ab = xy[1:-1] - xy[:-2]
        bc = xy[2:] - xy[1:-1]
        ac = xy[2:] - xy[:-2]

    @staticmethod
    def snaps(replay, max_angle, min_distance):
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
            ``|ab| > min_distance``.

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

        See Also
        --------
        :meth:`~.aim_correction_sam` for an alternative, unused approach
        involving velocity and jerk.
        """
        # when we leave mutliple frames with the same time values, they
        # sometimes get detected (falesly) as aim correction.
        # TODO Worth looking into a bit more to see if we can avoid it without
        # removing the frames entirely.
        t, xy = Investigator.remove_duplicate_t(replay.t, replay.xy)
        t = t[1:-1]

        # label three consecutive points (a b c) and the vectors between them
        # (ab, bc, ac)
        ab = xy[1:-1] - xy[:-2]
        bc = xy[2:] - xy[1:-1]
        ac = xy[2:] - xy[:-2]
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
        cos_beta = np.true_divide(num, denom, out=np.full_like(num, np.nan), where=denom!=0)
        # rounding issues makes cos_beta go out of arccos' domain, so restrict it
        cos_beta = np.clip(cos_beta, -1, 1)

        beta = np.rad2deg(np.arccos(cos_beta))

        min_AB_BC = np.minimum(AB, BC)
        dist_mask = min_AB_BC > min_distance
        # use less to avoid comparing to nan
        angle_mask = np.less(beta, max_angle, where=~np.isnan(beta))
        # boolean array of datapoints where both distance and angle requirements are met
        mask = dist_mask & angle_mask

        return [Snap(t, b, d) for (t, b, d) in zip(t[mask], beta[mask], min_AB_BC[mask])]

    @staticmethod
    def snaps_sam(replay_data, num_jerks, min_jerk):
        """
        Calculates the jerk at each moment in the Replay, counts the number of times
        it exceeds min_jerk and reports a positive if that number is over num_jerks.
        Also reports all suspicious jerks and their timestamps.

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
        # safely calculate the division and replace with zero if the divisor is zero
        # dtdT is sliced with 2: because differentiating drops one element for each order (slice (n - 1,) to (n - 3,))
        # d3xy is of shape (n - 3, 2) so dtdT is also reshaped from (n - 3,) to (n - 3, 1) to align the axes.
        jerk = np.divide(d3xy, dtdT[2:, None] ** 3, out=np.zeros_like(d3xy), where=dtdT[2:,None]!=0)

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
        frametimes = Investigator.frametimes(replay)
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
        # replay.t is cumsum so convert it back to "time since previous frame"
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

    # TODO add exception for 2b objects (>1 object at the same time) for current
    # version of notelock
    @staticmethod
    def hits(replay, beatmap):
        """
        Determines the hits (where any hitobject was hit for the first time)
        when playing ``replay`` against ``beatmap``

        Parameters
        ----------
        replay: :class:`~.Replay`
            The replay to determine the hits of when played against ``beatmap``.
        beatmap: :class:`slider.beatmap.Beatmap`
            The beatmap to determine the hits of when ``replay`` is played
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
            sliderbug_fixed = game_version >= Investigator.VERSION_SLIDERBUG_FIXED_STABLE
        else:
            sliderbug_fixed = game_version >= Investigator.VERSION_SLIDERBUG_FIXED_CUTTING_EDGE

        easy = Mod.EZ in replay.mods
        hard_rock = Mod.HR in replay.mods
        hitobjs = beatmap.hit_objects(easy=easy, hard_rock=hard_rock)

        OD = beatmap.od(easy=easy, hard_rock=hard_rock)
        CS = beatmap.cs(easy=easy, hard_rock=hard_rock)
        keydowns = Investigator.keydown_frames(replay)


        hits = []

        # stable converts OD (and CS), which are originally a float32, to a
        # double and this causes some hitwindows to be messed up when casted to
        # an int so we replicate this
        hitwindow = int(150 + 50 * (5 - float(np.float32(OD))) / 5)

        # attempting to match stable hitradius
        hitradius = np.float32(64 * ((1.0 - np.float32(0.7) * (float(np.float32(CS)) - 5) / 5)) / 2) * np.float32(1.00041)

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
                hitobj_end_time = hitobj_t + hitwindow
            elif isinstance(hitobj, Slider):
                hitobj_type = 1
                hitobj_end_time = hitobj.end_time.total_seconds() * 1000
            else:
                hitobj_type = 2
                hitobj_end_time = hitobj.end_time.total_seconds() * 1000

            # before sliderbug fix, notelock ended after hitwindow50
            if not sliderbug_fixed:
                notelock_end_time = hitobj_t + hitwindow
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

            if keydown_t <= hitobj_t - hitwindow:
                # pressing on a circle or slider during hitwindowmiss will cause
                #  a miss
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
                if keydown_t < hitobj_t + hitwindow and np.linalg.norm(keydown_xy - hitobj_xy) <= hitradius and hitobj_type != 2:
                    hits.append(Hit(hitobj, keydown_t, keydown_xy))

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

        return hits

    # TODO (some) code duplication with this method and a similar one in
    # ``Comparer``. Consolidate and move this method to utils?
    @staticmethod
    def remove_duplicate_t(t, data):
        t, t_sort = np.unique(t, return_index=True)
        data = data[t_sort]
        return (t, data)


class Snap():
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

    See Also
    --------
    :meth:`~.Investigator.aim_correction`
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


class Hit():
    """
    A hit on a hitobject when a replay is played against a beatmap. In osu!lazer
    terms, this would be a Judgement, though we do not count misses as a ``Hit``
    while lazer does count them as judgements.

    Parameters
    ----------
    hitobject: :class:`slider.beatmap.HitObject`
        The hitobject that was hit.
    t: float
        The time the hit occured.
    xy: list[float, float]
        The x and y position where the hit occured.
    """
    def __init__(self, hitobject, t, xy):
        self.hitobject = hitobject
        self.t = t
        self.xy = xy

    # TODO slider hitobjects don't define __eq__, pr that in
    def __eq__(self, other):
        return (self.hitobject == other.hitobject and self.t == other.t and
            self.xy == other.xy)

    def __hash__(self):
        return hash((self.hitobject, self.t, self.xy))
