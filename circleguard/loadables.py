import abc
import logging
from pathlib import Path
import os
import sqlite3
import random

import circleparse
import numpy as np
import wtc

from circleguard.enums import RatelimitWeight
from circleguard.mod import Mod
from circleguard.utils import TRACE, KEY_MASK
from circleguard.loader import Loader
from circleguard.span import Span
from circleguard.game_version import GameVersion, NoGameVersion

class Loadable(abc.ABC):
    """
    Represents one or multiple replays, which have replay data to be loaded
    from some additional source - the osu! api, local cache, or some other
    location.

    Parameters
    ----------
    cache: bool
        Whether to cache the replay data once loaded.
    """
    def __init__(self, cache):
        self.loaded = False
        self.cache = cache

    @abc.abstractmethod
    def load(self, loader, cache):
        """
        Loads the information this loadable needs to become fully loaded.
        Details left to the subclass implementation.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load this loadable with. Although subclasses may not
            end up using a :class:`~circleguard.loader.Loader` to load
            themselves (if they don't load anything from the osu api, for
            instance), a loader is still passed regardless.
        cache: bool
            Whether to cache the replay data once loaded. This argument
            comes from a parent—either a :class:`~.ReplayContainer` or
            :class:`~circleguard.circleguard.Circleguard` itself. Should the
            loadable already have a set ``cache`` value, that should take
            precedence over the option passed in this method, but if the
            loadable has no preference then it should respect the value passed
            here.
        """
        pass

    @abc.abstractmethod
    def __eq__(self, loadable):
        pass


class ReplayContainer(Loadable):
    """
    A Loadable that holds Replay subclasses, and which has an additional state
    between "unloaded" and "loaded" called "info loaded".

    ReplayContainers start unloaded and become info loaded when
    :meth:`~.load_info` is called. They become fully loaded when
    :meth:`~.load` is called (and if this is called when the ReplayContainer is
    in the unloaded state, :meth:`~Loadable.load` will load info first, then
    load the replays, effectively skipping the info loaded state),

    In the unloaded state, the container has no actual Replay objects. It may
    have limited knowledge about their number or type.

    In the info loaded state, the container has references to Replay objects,
    but those Replay objects are unloaded.

    In the loaded state, the Replay objects in the container are loaded.
    """
    def __init__(self, cache):
        super().__init__(cache)
        self.info_loaded = False

    def load(self, loader, cache=None):
        """
        Loads all :class:`~circleguard.loadables.Loadable`\s contained by this
        loadable container.

        Parameters
        ----------
        loader: :class:`~circleguard.loader.Loader`
            The loader to load the :class:`~circleguard.loadables.Loadable`\s
            with.
        """
        if self.loaded:
            return
        cascade_cache = cache if self.cache is None else self.cache
        self.load_info(loader)
        for replay in self.all_replays():
            replay.load(loader, cascade_cache)
        self.loaded = True

    @abc.abstractmethod
    def load_info(self, loader):
        pass

    @abc.abstractmethod
    def all_replays(self):
        """
        Returns all the :class:`~.Replay`\s in this loadable container.

        Warnings
        --------
        If you want an accurate list of :class:`~.Replay`\s in this instance,
        you must call :func:`~circleguard.circleguard.Circleguard.load` on this
        instance before :func:`~.all_replays`. Otherwise, this
        instance is not info loaded, and does not have a complete list of
        replays it represents.
        """
        pass

    def __len__(self):
        return len(self.all_replays())

    def __getitem__(self, key):
        replays = self.all_replays()
        if isinstance(key, slice):
            return replays[key.start:key.stop:key.step]
        return replays[key]

    def __iter__(self):
        return iter(self.all_replays())



class Map(ReplayContainer):
    """
    A map's top plays (leaderboard), as seen on the website.

    Parameters
    ----------
    map_id: int
        The map to represent the top plays for.
    span: str or Span
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the top two ``HD`` plays on the map are
        represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    """
    def __init__(self, map_id, span, mods=None, cache=None):
        super().__init__(cache)
        self.replays = []
        self.map_id = map_id
        self.mods = mods
        self.span = Span(span)

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, self.span, mods=self.mods):
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, Map):
            return False
        return (self.map_id == loadable.map_id and self.mods == loadable.mods
                and self.span == loadable.span)

    def __repr__(self):
        return (f"Map(map_id={self.map_id},cache={self.cache},mods={self.mods},"
                f"span={self.span},replays={self.replays},loaded={self.loaded})")

    def __str__(self):
        return f"Map {self.map_id}"


class User(ReplayContainer):
    """
    A user's top plays (pp-wise, as seen on the website).

    Parameters
    ----------
    user_id: int
        The user to represent the top plays for.
    span: str or Span
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~.enums.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented. <br>
        This is applied before ``span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the user's top two ``HD`` plays are represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``mods`` and ``span``
        are applied. True by default.
    """
    def __init__(self, user_id, span, mods=None, cache=None, available_only=True):
        super().__init__(cache)
        self.replays = []
        self.user_id = user_id
        self.span = Span(span)
        self.mods = mods
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.get_user_best(self.user_id, span=self.span, mods=self.mods):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, User):
            return False
        return (self.user_id == loadable.user_id and self.mods == loadable.mods
                and self.span == loadable.span)


class MapUser(ReplayContainer):
    """
    All replays on a map by a user, not just the top replay.

    Parameters
    ----------
    map_id: int
        The map to represent scores by `user_id` on.
    user_id: int
        The user to represent scores on `map_id` for.
    span: str or Span
        A comma separated list of ranges of plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``span`` is applied.
        True by default.
    """
    def __init__(self, map_id, user_id, span=Loader.MAX_MAP_SPAN, cache=None, available_only=True):
        super().__init__(cache)
        self.replays = []
        self.map_id = map_id
        self.user_id = user_id
        self.span = Span(span)
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        for info in loader.replay_info(self.map_id, span=self.span, user_id=self.user_id, limit=False):
            if self.available_only and not info.replay_available:
                continue
            self.replays.append(ReplayMap(info.map_id, info.user_id, info.mods, cache=self.cache, info=info))
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, MapUser):
            return False
        return (self.map_id == loadable.map_id and self.user_id == loadable.user_id
                and self.span == loadable.span)


class ReplayCache(ReplayContainer):
    """
    Contains replays represented by a circlecore database. Primarily useful
    to randomly sample these replays, rather than directly access them.

    Parameters
    ----------
    path: string
        The path to the database to load replays from.
    num_maps: int
        How many (randomly chosen) maps to load replays from.
    limit: int
        How many replays to load for each map. If we have less than ``limit``
        replays stored for a randomly chosen map, only the replays we have
        stored will be loaded.

    Notes
    -----
    :meth:`~.load_info` is an expensive operation for large databases created
    on circlecore version 4.3.5 or earlier, as they do not have the necessary
    indexes.
    For databases created in later versions, this is a nonissue and the lookup
    is fast.
    """
    def __init__(self, path, num_maps, num_replays):
        super().__init__(False)
        self.path = path
        self.num_maps = num_maps
        self.limit = num_replays * num_maps
        self.replays = []
        conn = sqlite3.connect(path)
        self.cursor = conn.cursor()

    def load_info(self, loader):
        if self.info_loaded:
            return
        map_ids = self.cursor.execute(
            """
            SELECT DISTINCT map_id
            FROM replays
            """
        ).fetchall()

        # flatten map_ids, because it's actually a list of lists
        map_ids = [item[0] for item in map_ids]
        chosen_maps = random.choices(map_ids, k=self.num_maps)

        subclauses = [f"map_id = {chosen_map}" for chosen_map in chosen_maps]
        where_clause = " OR ".join(subclauses)

        infos = self.cursor.execute(
            f"""
            SELECT user_id, map_id, replay_data, replay_id, mods
            FROM replays
            WHERE {where_clause}
            LIMIT {self.limit}
            """
        )

        for info in infos:
            r = CachedReplay(info[0], info[1], info[4], info[2], info[3])
            self.replays.append(r)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, other):
        return self.path == other.path


class ReplayDir(ReplayContainer):
    """
    A folder with replay files inside it.

    Notes
    -----
    Any files not ending in ``.osr`` are ignored.

    Warnings
    --------
    Nested directories are not support (yet). Any folders encountered will be
    ignored.
    """
    def __init__(self, dir_path, cache=None):
        super().__init__(cache)
        self.dir_path = Path(dir_path)
        if not self.dir_path.is_dir():
            raise ValueError(f"Expected path pointing to {self.dir_path} to be"
                " a directory")
        self.replays = []

    def load_info(self, loader):
        if self.info_loaded:
            return
        for path in os.listdir(self.dir_path):
            if not path.endswith(".osr"):
                continue
            replay = ReplayPath(self.dir_path / path)
            self.replays.append(replay)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, other):
        return self.dir_path == other.dir_path


class Replay(Loadable):
    """
    A replay played by a player.

    Parameters
    ----------
    weight: :class:`~.enums.RatelimitWeight`
        How much it 'costs' to load this replay from the api.
    cache: bool
        Whether to cache this replay once it is loaded.

    Attributes
    ----------
    game_version: :class:`~circleguard.game_version.GameVersion`
        Information about the version of osu! the replay was played on.
    timestamp: :class:`datetime.datetime`
        When the replay was played.
    map_id: int
        The id of the map the replay was played on, or 0 if
        unknown or on an unsubmitted map.
    user_id: int
        The id of the player who played the replay, or 0 if unknown
        (if the player is restricted, for instance). Note that if the
        user id is known, even if the user is restricted, it should still be
        given instead of 0.
    username: str
        The username of the player who played the replay.
    mods: :class:`~.enums.ModCombination`
        The mods the replay was played with.
    replay_id: int
        The id of the replay, or 0 if the replay is unsubmitted.
    keydowns: ndarray[int]
        The keydowns for each frame of the replay. Keydowns are the keys pressed
        in that frame that were not pressed in the previous frame. See
        :meth:`~.keydowns` for more details.
    t: ndarray[int]
        A 1d array containing the timestamp for each frame. <br>
        This is only nonnull after the replay has been loaded.
    xy: ndarray[float]
        A 2d, two column array, containing the ``x`` and ``y`` coordinates of
        each frame in the first and second column respectively. <br>
        This is only nonnull after the replay has been loaded.
    k: ndarray[int]
        A 1d array containing the keys pressed for each frame. <br>
        This is only nonnull after the replay has been loaded.
    """
    def __init__(self, weight, cache):
        super().__init__(cache)
        self.weight = weight

        # These attributes might or might not be set once the replay loads.
        # Ideally, a replay would provide all of these attributes, but there are
        # some cases when only a subset is available. <br>
        # If only some of these attributes are set after the replay is loaded,
        # some ``Circleguard`` methods may reject this replay, as it does not
        # contain the information necessary to do whatever the method needs to.
        # <br>
        # For instance, if the replay provides ``replay_data`` but not ``mods``,
        # ``Circleguard#similarity`` will reject it, as we will not know whether
        # whether ``Mod.HR`` was enabled on the replay, and thus whether to flip
        # the replay before comparing it to another one.

        # replays don't have any information about their game version by
        # default. Subclasses might set this if they have more information to
        # provide about their version, whether on instantiation or after being
        # loaded.
        self.game_version = NoGameVersion()
        self.timestamp    = None
        self.map_id       = None
        self.username     = None
        self.user_id      = None
        self.mods         = None
        self.replay_id    = None
        self.replay_data  = None

        # These attributes remain ``None``` when replay is unloaded or loaded
        # but with no data.
        self.t            = None
        self.xy           = None
        self.k            = None
        self._keydowns    = None

    def has_data(self):
        """
        Whether this replay has any replay data.

        Returns
        -------
        bool
            Whether this replay has any replay data.

        Notes
        -----
        If this replay is unloaded, it is guaranteed to not have any replay
        data. But if the replay is loaded, it is not guaranteed to have any
        replay data. Some replays do not have any replay data available from
        the api, even after being loaded.
        """
        if not self.loaded:
            return False
        return bool(self.replay_data)

    def _process_replay_data(self, replay_data):
        """
        Preprocesses the replay data (turns it into numpy arrays) for fast
        manipulation when investigating.

        Paramters
        ---------
        replay_data: list[:class:`~circleparse.Replay.ReplayEvent`]
            A list of :class:`~circleparse.Replay.ReplayEvent` objects,
            representing the actual data of the replay. If the replay could not
            be loaded, this should be ``None``.

        Notes
        -----
        This method must be called before a replay can be considered loaded
        (ie before you set ``loaded`` to ``True``).
        """
        self.replay_data = replay_data
        # replay wasn't available, can't preprocess the data
        if replay_data is None:
            return

        # remove invalid zero time frame at beginning of replay
        # https://github.com/ppy/osu/blob/1587d4b26fbad691242544a62dbf017a78705ae3/osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L242-L245
        if replay_data[0].time_since_previous_action == 0:
            replay_data = replay_data[1:]

        # t, x, y, k
        data = [[], [], [], []]
        ## TODO try to use a peekable iterator to use an iter for above as well
        # use an iter an an optimization so we don't recreate the list when
        # taking (and removing) the first element
        replay_data = iter(replay_data)
        # The following comments in this method are guesswork, but seems to
        # accurately describe replays. This references the "first" frame
        # assuming that we have already removed the truly first zero time
        # frame, if it is present. So technically the "first" frame below may
        # be the second frame.
        # There are two possibilities for replays:
        # * for replays with a skip in the beginning, the first frame time is
        #   the skip duration. The next frame after that will have a negative
        #   time, to account for the replay data before the skip.
        # * for replays without a skip in the beginning, the first frame time
        #   is -1.
        # Since in the first case the first frame time is a large positive,
        # this would make ``highest_running_t`` large and cause all replay data
        # before the skip to be ignored. To solve this, we initialize
        # ``running_t`` to the first frame's time.
        running_t = next(replay_data).time_since_previous_action
        # We consider negative time frames in the middle of replays to be
        # valid, with a caveat. Their negative time is counted toward
        # ``running_t`` (that is, decreases ``running_t``), but any frames
        # after it are ignored, until the total time passed of ignored frames
        # is greater than or equal to the negative frame.
        # There's one more catch - the frame that brings us *out* of this
        # "negative time" section where we're ignoring frames will cause a
        # special frame to be inserted, which has the same time as the frame
        # that brought us *into* the negative time section, and specially
        # calculated x and y positions. Details below.
        # I do not know why stable treats negative time frames in this way.
        # It is not what lazer does, as far as I can tell. But it is the only
        # reasonable explanation for stable behavior. This solution may not,
        # however, be the canonical solution.
        highest_running_t = np.NINF
        # The last positive frame we encountered before entering a negative
        # section.
        last_positive_frame = None
        # the running time when we encountered ``last_positive_frame``. We need
        # to save this as we do not store this information in each individual
        # frame.
        last_positive_frame_cum_time = None
        previous_frame = None
        for e in replay_data:
            # check if we were in a negative section of the play at the
            # previous frame (f0) before applying the current frame (f1), so we
            # can apply special logic if f1 is the frame that gets us out of
            # the negative section.
            was_in_negative_section = running_t < highest_running_t

            e_t = e.time_since_previous_action
            running_t += e_t
            highest_running_t = max(highest_running_t, running_t)
            if running_t < highest_running_t:
                # if we weren't in a negative section in f0, f1 is the first
                # frame to bring us into one, so f0 is the last positive frame.
                if not was_in_negative_section:
                    last_positive_frame = previous_frame
                    # we want to set it to the cumulative time before f1
                    # was processed, so subtract out the current e_t
                    last_positive_frame_cum_time = running_t - e_t
                previous_frame = e
                continue

            # if we get here, f1 brought us out of the negative section. In
            # this case, osu! actually inserts a new frame, with:
            # * t = the cumulative time at the last positive frame (yes, this
            #   means there are two frames at the same time in the replay
            #   playback).
            # * x, y = a weighted average between the positions of f0 and f1,
            #   weighted by how close the last positive frame's time is to each
            #   of the two frames' times.
            # * k = the keypresses of the last positive frame.
            if was_in_negative_section:
                data[0].append(last_positive_frame_cum_time)

                # this is [running_t at f0, running_t at f1], to interpolate
                # the last positive frame's time between.
                xp = [running_t - e_t, running_t]

                fp = [previous_frame.x, e.x]
                x = np.interp(last_positive_frame_cum_time, xp, fp)
                data[1].append(x)

                fp = [previous_frame.y, e.y]
                y = np.interp(last_positive_frame_cum_time, xp, fp)
                data[2].append(y)

                data[3].append(last_positive_frame.keys_pressed)

            data[0].append(running_t)
            data[1].append(e.x)
            data[2].append(e.y)
            data[3].append(e.keys_pressed)
            previous_frame = e

        block = np.array(data)

        t = np.array(block[0], dtype=int)
        xy = np.array([block[1], block[2]], dtype=float).T
        k = np.array(block[3], dtype=int)

        # sort our data by t. Stable so we don't reorder frames with equal
        # times
        t_sort = np.argsort(t, kind="stable")
        t = t[t_sort]
        xy = xy[t_sort]
        k = k[t_sort]

        self.t = t
        self.xy = xy
        self.k = k

    @property
    def keydowns(self):
        """
        A list of the keys pressed for each frame that were not pressed in the
        previous frame.

        Examples
        --------
        If the first frame (``f1``) has keys ``K1`` and ``f2`` has keys
        ``K1 + K2``, then ``keydowns[1]`` is ``K2``.
        """
        if not self.has_data():
            return None
        # can't do `if not self._keydowns` because the truth value of an
        # ndarray is ambiguous
        if self._keydowns is None:
            keypresses = self.k & KEY_MASK
            self._keydowns = keypresses & ~np.insert(keypresses[:-1], 0, 0)
        return self._keydowns

    def __repr__(self):
        return (f"Replay(timestamp={self.timestamp},map_id={self.map_id},"
            f"user_id={self.user_id},mods={self.mods},"
            f"replay_id={self.replay_id},weight={self.weight},"
            f"loaded={self.loaded},username={self.username})")

    def __str__(self):
        return f"Replay by {self.username} on {self.map_id}"


class ReplayMap(Replay):
    """
    A :class:`~.Replay` that was submitted to online servers.

    Parameters
    ----------
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    mods: ModCombination
        The mods the replay was played with. If ``None``, the
        highest scoring replay of ``user_id`` on ``map_id`` will be loaded,
        regardless of mod combination. Otherwise, the replay with ``mods``
        will be loaded.
    cache: bool
        Whether to cache this replay once it is loaded.
    """

    def __init__(self, map_id, user_id, mods=None, cache=None, info=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.info = info
        if info:
            self.timestamp = info.timestamp
            self.map_id = info.map_id
            self.user_id = info.user_id
            self.username = info.username
            self.replay_id = info.replay_id
            self.mods = info.mods

    def load(self, loader, cache):
        """
        Loads the data for this replay from the api.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``).

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method is finished.
        """
        # only listen to the parent's cache if ours is not set. Lower takes
        # precedence
        cache = cache if self.cache is None else self.cache
        self.log.debug("Loading %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return
        if self.info:
            info = self.info
        else:
            info = loader.replay_info(self.map_id, user_id=self.user_id, mods=self.mods)

        self.timestamp = info.timestamp
        # estimate version with timestamp, this is only accurate if the user
        # keeps their game up to date
        self.game_version = GameVersion.from_datetime(self.timestamp, concrete=False)
        self.username = info.username
        self.mods = info.mods
        self.replay_id = info.replay_id

        replay_data = loader.replay_data(info, cache=cache)
        self._process_replay_data(replay_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    def __eq__(self, loadable):
        """
        Whether the two maps are equal.

        Notes
        -----
        This does not take into account the
        ``cache`` attribute, because equality here means "do they represent the
        same replays".
        """
        if not isinstance(loadable, ReplayMap):
            return False
        if self.has_data() and loadable.has_data():
            return self.replay_data == loadable.replay_data
        return (self.map_id == loadable.map_id and
            self.user_id == loadable.user_id and self.mods == loadable.mods)

    def __hash__(self):
        return hash((self.map_id, self.user_id, self.mods))

    def __repr__(self):
        if self.loaded:
            return (f"ReplayMap(timestamp={self.timestamp},map_id={self.map_id}"
            f",user_id={self.user_id},mods={self.mods},cache={self.cache},"
            f"replay_id={self.replay_id},loaded={self.loaded},"
            f"username={self.username})")
        return (f"ReplayMap(map_id={self.map_id},user_id={self.user_id},"
                f"mods={self.mods},cache={self.cache},loaded={self.loaded})")

    def __str__(self):
        return (f"{'Loaded' if self.loaded else 'Unloaded'} ReplayMap by "
            f"{self.user_id} on {self.map_id}")


class ReplayPath(Replay):
    """
    A :class:`~.Replay` saved locally in a ``.osr`` file.

    Parameters
    ----------
    path: str or :class:`os.PathLike`
        The path to the replay file.
    cache: bool
        Whether to cache this replay once it is loaded. Note that currently
        we do not cache :class:`~.ReplayPath` regardless of this parameter.
    """

    def __init__(self, path, cache=None):
        super().__init__(RatelimitWeight.LIGHT, cache)
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = Path(path).absolute()
        self.beatmap_hash = None

    def load(self, loader, cache):
        """
        Loads the data for this replay from the osr file.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``). Note that currently
            we do not cache :class:`~.ReplayPath` regardless of this parameter.

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method is finished.
        """

        self.log.debug("Loading ReplayPath %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        loaded = circleparse.parse_replay_file(self.path)
        self.game_version = GameVersion(loaded.game_version, concrete=True)
        self.timestamp = loaded.timestamp
        self.map_id = loader.map_id(loaded.beatmap_hash)
        self.username = loaded.player_name
        # our `user_id` attribute is lazy loaded, so we need to retain the
        # `Loader#user_id` function to use later to load it.
        self._user_id_func = loader.user_id
        self._user_id = None
        self.mods = Mod(loaded.mod_combination)
        self.replay_id = loaded.replay_id
        self.beatmap_hash = loaded.beatmap_hash

        self._process_replay_data(loaded.play_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    @property
    def user_id(self):
        # we don't have a user_id_func if we're not loaded, so early return
        if not self.loaded:
            return None
        if not self._user_id:
            self._user_id = self._user_id_func(self.username)
        return self._user_id

    @user_id.setter
    def user_id(self, user_id):
        self._user_id = user_id

    def __eq__(self, loadable):
        """
        Whether these replay paths are equal.

        Notes
        -----
        If one or both replay paths don't have replay data, this checks path
        equality. If both replay paths have replay data, this checks the
        equality of their replay data.
        <br>
        The reason we don't check path after both are loaded is to avoid
        true in situations like this:

        ```
        r1 = ReplayPath("./1.osr")
        cg.load(r1)
        # change the file located at ./1.osr to another osr file
        r2 = ReplayPath("./1.osr")
        cg.load(r2)
        r1 == r2 # should be False, as they have differing replay data
        ```
        """
        if not isinstance(loadable, ReplayPath):
            return False
        if self.has_data() and loadable.has_data():
            return self.replay_data == loadable.replay_data
        return self.path == loadable.path

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        if self.loaded:
            return (f"ReplayPath(path={self.path},map_id={self.map_id},"
                f"user_id={self.user_id},mods={self.mods},"
                f"replay_id={self.replay_id},weight={self.weight},"
                f"loaded={self.loaded},username={self.username})")
        return (f"ReplayPath(path={self.path},weight={self.weight},"
                f"loaded={self.loaded})")

    def __str__(self):
        if self.loaded:
            return (f"Loaded ReplayPath by {self.username} on {self.map_id} at"
                f" {self.path}")
        return f"Unloaded ReplayPath at {self.path}"


class ReplayString(Replay):
    """
    A :class:`~.Replay` saved locally in a ``.osr`` file, when the file has
    already been read as a string.

    Parameters
    ----------
    replay_data_str: str
        The contents of the replay file as a string.
    cache: bool
        Whether to cache this replay once it is loaded. Note that currently
        we do not cache :class:`~.ReplayString` regardless of this parameter.
    """

    def __init__(self, replay_data_str, cache=None):
        super().__init__(RatelimitWeight.LIGHT, cache)
        self.log = logging.getLogger(__name__ + ".ReplayString")
        self.replay_data_str = replay_data_str
        self.beatmap_hash = None

    def load(self, loader, cache):
        """
        Loads the data for this replay from the string replay data.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``). Note that currently
            we do not cache :class:`~.ReplayString` regardless of this
            parameter.

        Notes
        -----
        If ``replay.loaded`` is ``True``, this method has no effect.
        ``replay.loaded`` is set to ``True`` after this method is finished.
        """

        self.log.debug("Loading ReplayString %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        loaded = circleparse.parse_replay(self.replay_data_str, pure_lzma=False)
        self.game_version = GameVersion(loaded.game_version, concrete=True)
        self.timestamp = loaded.timestamp
        self.map_id = loader.map_id(loaded.beatmap_hash)
        self.username = loaded.player_name
        # our `user_id` attribute is lazy loaded, so we need to retain the
        # `Loader#user_id` function to use later to load it.
        self._user_id_func = loader.user_id
        self._user_id = None
        self.mods = Mod(loaded.mod_combination)
        self.replay_id = loaded.replay_id
        self.beatmap_hash = loaded.beatmap_hash

        self._process_replay_data(loaded.play_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    @property
    def user_id(self):
        # we don't have a user_id_func if we're not loaded, so early return
        if not self.loaded:
            return None
        if not self._user_id:
            self._user_id = self._user_id_func(self.username)
        return self._user_id

    @user_id.setter
    def user_id(self, user_id):
        self._user_id = user_id

    def __eq__(self, loadable):
        if not isinstance(loadable, ReplayString):
            return False
        return self.replay_data_str == loadable.replay_data_str

    def __hash__(self):
        return hash(self.replay_data_str)

    def __repr__(self):
        if self.loaded:
            return (f"ReplayString(len(replay_data_str)={len(self.replay_data_str)},"
                    f"map_id={self.map_id},user_id={self.user_id},mods={self.mods},"
                    f"replay_id={self.replay_id},weight={self.weight},"
                    f"loaded={self.loaded},username={self.username})")
        return f"ReplayString(len(replay_data_str)={len(self.replay_data_str)})"

    def __str__(self):
        if self.loaded:
            return f"Loaded ReplayString by {self.username} on {self.map_id}"
        return (f"Unloaded ReplayString with {len(self.replay_data_str)} "
            "chars of data")


class ReplayID(Replay):
    def __init__(self, replay_id, cache=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.replay_id = replay_id

    def load(self, loader, cache):
        # TODO file github issue about loading info from replay id, right now we
        # can literally only load the replay data which is pretty useless if we
        # don't have a map id or the mods used
        cache = cache if self.cache is None else self.cache
        replay_data = loader.replay_data_from_id(self.replay_id, cache)
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        return self.replay_id == other.replay_id

    def __hash__(self):
        return hash(self.replay_id)

class CachedReplay(Replay):
    def __init__(self, user_id, map_id, mods, replay_data, replay_id):
        super().__init__(RatelimitWeight.NONE, False)
        self.user_id = user_id
        self.map_id = map_id
        self.mods = Mod(mods)
        self.replay_data = replay_data
        self.replay_id = replay_id

    def load(self, loader, cache):
        if self.loaded:
            return
        decompressed = wtc.decompress(self.replay_data)
        replay_data = circleparse.parse_replay(decompressed, pure_lzma=True).play_data
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        return self.replay_id == other.replay_id

    def __hash__(self):
        return hash(self.replay_id)
