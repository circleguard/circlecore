from enum import Enum, auto

import numpy as np

from circleguard.utils import check_param
from circleguard.hitobjects import Hitobject

class JudgmentType(Enum):
    Hit300 = auto()
    Hit100 = auto()
    Hit50 = auto()
    Miss = auto()

class Judgment:
    """
    A judgment on a hitobject. A "judgment" is either a hit or a miss, with
    a hit being further classified as a 300, 100, or 50.

    Parameters
    ----------
    hitobject: :class:`slider.beatmap.HitObject`
        The hitobject being judged. This is converted to a
        :class:`circleguard.hitobjects.Hitobject`.
    replay: :class:`circleguard.loadables.Replay`
        The replay this judgment was made on.
    beatmap: :class:`slider.beatmap.Beatmap`
        The beatmap this judgment was made on.
    type: :class:`JudgmentType`
        The type of this judgment (either Hit300, Hit100, or Hit50, or Miss).
    """
    def __init__(self, hitobject, replay, beatmap, type_):
        # TODO remove `already_converted=True` when
        # https://github.com/llllllllll/slider/issues/80 is fixed
        self.hitobject = Hitobject.from_slider_hitobj(hitobject, replay,
            beatmap, True)
        self.type = type_

class Miss(Judgment):
    """
    A miss on a hitobject when a replay is played against a beatmap.
    """
    def __init__(self, hitobject, replay, beatmap):
        super().__init__(hitobject, replay, beatmap, JudgmentType.Miss)

class Hit(Judgment):
    """
    A hit on a hitobject when a replay is played against a beatmap.

    Parameters
    ----------
    hitobject: :class:`slider.beatmap.HitObject`
        The hitobject that was hit. This is converted to a
        :class:`circleguard.hitobjects.Hitobject`.
    t: float
        The time the hit occured.
    xy: list[float, float]
        The x and y position where the hit occured.
    replay: :class:`circleguard.loadables.Replay`
        The replay this hit was made on.
    beatmap: :class:`slider.beatmap.Beatmap`
        The beatmap this hit was made on.
    type: :class:`JudgmentType`
        The type of this hit (either Hit300, Hit100, or Hit50).
    """
    def __init__(self, hitobject, t, xy, replay, beatmap, type_):
        super().__init__(hitobject, replay, beatmap, type_)
        # TODO remove ``t`` in core 6.0.0, ``time`` is more intuitive. ``x`` and
        # ``y`` are fine as is though since there's no longer name for them.
        self.t = t
        self.time = t
        self.xy = xy
        self.x = xy[0]
        self.y = xy[1]
        self.type = type_

    def distance(self, *, to):
        """
        The distance from this hit to either the center or edge of its
        hitobject.

        Parameters
        ----------
        to: {"center", "edge"}
            If ``center``, the distance from this hit to the center of its
            hitobject is calculated. If ``edge``, the distance from this hit to
            the edge of its hitobject is calculated.
        Returns
        -------
        float
            The distance from this hit to either the center or edge of its
            hitobject.
        """
        check_param(to, ["center", "edge"])

        hitobj_xy = self.hitobject.xy

        if to == "edge":
            dist = np.linalg.norm(self.xy - hitobj_xy) - self.hitobject.radius
            # value is negative since we're inside the hitobject, so take abs
            return abs(dist)

        if to == "center":
            return np.linalg.norm(self.xy - hitobj_xy)

    def within(self, distance):
        """
        Whether the hit was within ``distance`` of the edge of its hitobject.

        Parameters
        ----------
        distance: float
            How close, in pixels, to the edge of the hitobject the hit has to
            be.

        Returns
        -------
        bool
            Whether the hit was within ``distance`` of the edge of its
            hitobject.

        Notes
        -----
        The lower the value, the closer to the edge the hit occurred. This value
        can never be greater than the radius of the hitobject.
        """

        return self.distance(to="edge") < distance

    def error(self):
        """
        How many milliseconds off this hit was from being a perfectly on time
        hit. If negative, this was an early hit. If positive, this was a late
        hit. If 0, this was a perfect hit.

        Returns
        -------
        float
            How many milliseconds off this hit was from being perfectly on time.
        """
        return self.time - self.hitobject.time

    def __eq__(self, other):
        return (self.hitobject == other.hitobject and self.t == other.t and
            self.xy == other.xy)

    def __hash__(self):
        return hash((self.hitobject, self.t, self.xy))

    def __repr__(self):
        return f"Hit(hitobject={self.hitobject},t={self.t},xy={self.xy}"

    def __str__(self):
        return f"({self.x}, {self.y}) at t {self.t}"
