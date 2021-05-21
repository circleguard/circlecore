import numpy as np
from slider.beatmap import Circle as SliderCircle
from slider.beatmap import Slider as SliderSlider
from slider.beatmap import Spinner as SliderSpinner
from slider.mod import circle_radius

from circleguard.mod import Mod

# We define our own hitobjects as the slider library's hitobjects have too many
# attributes and methods we don't care about, and they also lock position
# behind an extra attribute access (``hitobj.position.x``` vs ``hitobj.x``)
# which I'm not a fan of.
# Another necessary change is our hitobjects are "replay/map aware", which means
# they know how large they are (or potentially how difficult they are to hit
# as a result of OD if that is necessary in the future) and where they are (for
# HR) because we know with what mods and on what map the hitobject was played
# with.

class Hitobject:
    """
    A Hitobject in osu! gameplay, with a time and a position.
    """
    def __init__(self, time, xy):
        # TODO remove ``t`` in core 6.0.0, ``time`` should be preferred
        self.t = time
        self.time = time
        self.xy = xy
        self.x = xy[0]
        self.y = xy[1]

    @classmethod
    def from_slider_hitobj(cls, hitobj, replay, beatmap, already_converted=False):
        """
        Instantiates a circleguard hitobject from a
        :class:`slider.beatmap.HitObject`, a
        :class:`circleguard.loadables.Replay`, that the hitobject was hit on,
        and a :class:`slider.beatmap.Beatmap` that the hitobject is found in.

        The `already_converted` parameter is only to work around
        https://github.com/llllllllll/slider/issues/80 and will be removed when
        it is fixed.
        """
        easy = Mod.EZ in replay.mods
        hard_rock = Mod.HR in replay.mods
        CS = beatmap.cs(easy=easy, hard_rock=hard_rock)

        # Convert to ms.
        t = hitobj.time.total_seconds() * 1000
        # Due to floating point errors, ``t`` could actually be something
        # like ``129824.99999999999`` or ``128705.00000000001``, so round to the
        # nearest int.
        t = int(round(t))

        if hard_rock and not already_converted:
            hitobj = hitobj.hard_rock

        xy = [hitobj.position.x, hitobj.position.y]
        xy = np.array(xy)

        radius = circle_radius(CS)

        if isinstance(hitobj, SliderCircle):
            return Circle(t, xy, radius)
        if isinstance(hitobj, SliderSlider):
            return Slider(t, xy, radius)
        if isinstance(hitobj, SliderSpinner):
            return Spinner(t, xy)

    def __eq__(self, other):
        return self.time == other.time and self.xy == other.xy

    def __hash__(self):
        return hash((self.time, self.xy))


class Circle(Hitobject):
    """
    A circle in osu! gameplay, with a time, position, and radius.
    """
    def __init__(self, time, xy, radius):
        super().__init__(time, xy)
        self.radius = radius

    def __eq__(self, other):
        return (self.time == other.time and self.xy == other.xy and
            self.radius == other.radius)

    def __hash__(self):
        return hash((self.time, self.xy, self.radius))


class Slider(Hitobject):
    """
    A slider in osu! gameplay, with a time, position, and radius.
    """
    def __init__(self, time, xy, radius):
        super().__init__(time, xy)
        self.radius = radius

    def __eq__(self, other):
        return (self.time == other.time and self.xy == other.xy and
            self.radius == other.radius)

    def __hash__(self):
        return hash((self.time, self.xy, self.radius))


class Spinner(Hitobject):
    """
    A spinner in osu! gameplay, with a time and position.
    """
    def __init__(self, time, xy):
        super().__init__(time, xy)
