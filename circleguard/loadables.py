import abc
import logging
from pathlib import Path
import os
import sqlite3
import random

import osrparse
from osrparse import ReplayEventOsu
import numpy as np
import wtc

from circleguard.mod import Mod
from circleguard.utils import TRACE, KEY_MASK, RatelimitWeight
from circleguard.loader import Loader
from circleguard.span import Span
from circleguard.game_version import GameVersion, NoGameVersion
from circleguard.map_info import MapInfo


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
            Note: ``loader`` may be ``None``. This means that whatever is
            loading the loadable does not have api access and cannot provide a
            loader. If your loadable requires a loader to properly load itself,
            raise an error on a null ``loader``. If your loadable can load
            itself without a ``loader``, proceed as planned and ignore the null
            ``loader``.
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


class LoadableContainer(Loadable):
    """
    A Loadable that holds Loadables, which may be ``ReplayContainer``\s or
    ``Replay``\s.

    Parameters
    ----------
    loadables: list[:class:`~.Loadable`]
        The loadables to hold.
    cache: bool
        Whether to cache the loadables once they are loaded. This will be
        overriden by a ``cache`` option set by a :class:`~Loadable` in
        ``loadables``. This only affects child loadables when they do not have
        a ``cache`` option set.

    Notes
    -----
    This class is intended for situations when you have a list of replays and
    replay containers, but no way to separate or distinguish them. If you want
    to get, say, all the replays out of that list (whether they come from
    replay subclasses already in the list, or the replays held by a replay
    container in the list), this loadable container class has the logic to do
    that for you:

    >>> lc = LoadableContainer(mixed_loadable_list)
    >>> replays = lc.all_replays()

    It can also be useful to info load the replay containers in the list,
    without first filtering the list to remove any replay subclasses:

    >>> cg.load_info(lc)
    >>> # all loadable containers in the list are now info loaded
    >>> cg.load(lc)
    >>> # all loadables in the list are now loaded

    You are very unlikely to want to subclass this class. If you want to add a
    new loadable that holds replays, subclass ``ReplayContainer``.
    """

    def __init__(self, loadables, cache=None):
        super().__init__(cache)
        self.loadables = loadables

    def all_replays(self):
        """
        All the :class:`~.Replay`\s in this loadable container.

        Returns
        -------
        list[:class:`~Replay`]
            All the replays in this loadable container.

        Warnings
        --------
        This list may be incomplete if you do not call
        :meth:`~circleguard.circleguard.Circleguard.load_info` on this loadable
        container first, as any replay containers held in this container will
        likely not have references to their replays yet.
        """
        replays = []
        for loadable in self.loadables:
            if isinstance(loadable, ReplayContainer):
                replays += loadable.all_replays()
            else:
                # loadable is a Replay if it's not a ReplayContainer
                replays.append(loadable)
        return replays

    def load(self, loader, cache):
        cascade_cache = cache if self.cache is None else self.cache
        for loadable in self.loadables:
            loadable.load(loader, cascade_cache)

    def load_info(self, loader):
        for loadable in self.loadables:
            if isinstance(loadable, ReplayContainer):
                loadable.load_info(loader)

    def __eq__(self, loadable):
        if not isinstance(loadable, LoadableContainer):
            return False
        return self.all_replays() == loadable.all_replays()

    def __len__(self):
        return len(self.loadables)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.loadables[key.start:key.stop:key.step]
        return self.loadables[key]

    def __iter__(self):
        return iter(self.loadables)


class ReplayContainer(Loadable):
    """
    A Loadable that holds Replay subclasses, and which has an additional state
    between "unloaded" and "loaded" called "info loaded".

    ReplayContainers start unloaded and become info loaded when
    :meth:`~circleguard.circleguard.Circleguard.load_info` is called. They
    become fully loaded when :meth:`~.circleguard.circleguard.Circleguard.load`
    is called (and if this is called when the ReplayContainer is in the unloaded
    state, :meth:`~Loadable.load` will load info first, then load the replays,
    effectively skipping the info loaded state).

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
        you must call :func:`~circleguard.circleguard.Circleguard.load_info` on
        this instance before
        :func:`~circleguard.loadables.ReplayContainer.all_replays`. Otherwise,
        this instance is not info loaded, and does not have a complete list of
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
    beatmap_id: int
        The map to represent the top plays for.
    span: str or Span
        A comma separated list of ranges of top plays to retrieve.
        ``span="1-3,6,2-4"`` -> replays in the range ``[1,2,3,4,6]``.
    mods: :class:`~circleguard.mod.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented.
        |br|
        This is applied before ``span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the top two ``HD`` plays on the map are
        represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    """
    def __init__(self, beatmap_id, span, mods=None, cache=None):
        super().__init__(cache)
        self.replays = []
        self.beatmap_id = beatmap_id
        self.mods = mods
        self.span = Span(span)

        # TODO remove in core 6.0.0
        self.map_id = beatmap_id

    def load_info(self, loader):
        if self.info_loaded:
            return
        if not loader:
            raise ValueError("A Map cannot be info loaded without api access")
        for score in loader.replay_info(self.beatmap_id, span=self.span,
            mods=self.mods):
            r = ReplayMap(score.beatmap_id, score.user_id, score.mods,
                cache=self.cache, info=score)
            self.replays.append(r)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, Map):
            return False
        return (self.beatmap_id == loadable.beatmap_id
                and self.mods == loadable.mods and self.span == loadable.span)

    def __repr__(self):
        return (f"Map(beatmap_id={self.beatmap_id},cache={self.cache},"
            f"mods={self.mods},span={self.span},replays={self.replays},"
            f"loaded={self.loaded})")

    def __str__(self):
        return f"Map {self.beatmap_id}"


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
    mods: :class:`~circleguard.mod.ModCombination`
        If passed, only represent replays played with this exact mod
        combination. Due to limitations with the api, fuzzy matching is not
        implemented.
        |br|
        This is applied before ``span``. That is, if ``span="1-2"``
        and ``mods=Mod.HD``, the user's top two ``HD`` plays are represented.
    cache: bool
        Whether to cache the replays once they are loaded.
    available_only: bool
        Whether to represent only replays that have replay data available.
        Replays are filtered on this basis after ``mods`` and ``span``
        are applied. True by default.
    """
    def __init__(self, user_id, span, mods=None, cache=None, \
        available_only=True):
        super().__init__(cache)
        self.replays = []
        self.user_id = user_id
        self.span = Span(span)
        self.mods = mods
        self.available_only = available_only

    def load_info(self, loader):
        if self.info_loaded:
            return
        if not loader:
            raise ValueError("A User cannot be info loaded without api access")
        # thanks to api v1 weirdness, depending on the endpoint we use to
        # retrieve the Score model, the username may or may not be present (to
        # be explicit, `get_scores` includes the username, `get_user_best` does
        # not). We guarantee that this attribute is present for `ReplayMap`s
        # but when we pass an override `info` to it here it won't retrieve
        # the username, meaning it gets stuck with a `None` username. To fix
        # this just manually retrieve the username once here and set
        # `info.username` manually.
        # Ideally this attribute would be lazy-loaded in some form so this call
        # isn't hit until required, but doing so would require more complexity
        # than I'm comfortable with for such minor savings (one api call per
        # unique user, since `loader.username` is @lru_cached).
        username = loader.username(self.user_id)
        for info in loader.get_user_best(self.user_id, self.span, self.mods):
            if self.available_only and not info.replay_available:
                continue
            info.username = username
            r = ReplayMap(info.beatmap_id, info.user_id, info.mods, self.cache,
                info=info)
            self.replays.append(r)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, User):
            return False
        return (self.user_id == loadable.user_id and self.mods == loadable.mods
                and self.span == loadable.span)

    def __str__(self):
        return f"User {self.user_id}"


class MapUser(ReplayContainer):
    """
    All replays on a map by a user, not just the top replay.

    Parameters
    ----------
    beatmap_id: int
        The beatmap to represent scores by `user_id` on.
    user_id: int
        The user to represent scores on `beatmap_id` for.
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
    def __init__(self, beatmap_id, user_id, span=Loader.MAX_MAP_SPAN, \
        cache=None, available_only=True):
        super().__init__(cache)
        self.replays = []
        self.beatmap_id = beatmap_id
        self.user_id = user_id
        self.span = Span(span)
        self.available_only = available_only

        # TODO remove in core 6.0.0
        self.map_id = beatmap_id

    def load_info(self, loader):
        if self.info_loaded:
            return
        if not loader:
            raise ValueError("A MapUser cannot be info loaded without "
                "api access")
        for info in loader.replay_info(self.beatmap_id, span=self.span,
            user_id=self.user_id, limit=False):
            if self.available_only and not info.replay_available:
                continue
            r = ReplayMap(info.beatmap_id, info.user_id, info.mods, self.cache,
                info=info)
            self.replays.append(r)
        self.info_loaded = True

    def all_replays(self):
        return self.replays

    def __eq__(self, loadable):
        if not isinstance(loadable, MapUser):
            return False
        return (self.beatmap_id == loadable.beatmap_id and
            self.user_id == loadable.user_id and self.span == loadable.span)

    def __str__(self):
        return f"MapUser for {self.user_id} on /b/{self.beatmap_id}"

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
        How many replays to load for each map.

    Notes
    -----
    :meth:`~circleguard.circleguard.Circleguard.load_info` is an expensive
    operation for large databases created on circlecore version 4.3.5 or
    earlier, as they do not have the necessary indexes.
    |br|
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

        # TODO LIMIT clause isn't quite right here, some maps will have less
        # than ``num_replays`` stored
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
    weight: :class:`~circleguard.utils.RatelimitWeight`
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
    mods: :class:`~circleguard.mod.ModCombination`
        The mods the replay was played with.
    replay_id: int
        The id of the replay, or 0 if the replay is unsubmitted.
    keydowns: ndarray[int]
        The keydowns for each frame of the replay. Keydowns are the keys pressed
        in that frame that were not pressed in the previous frame. See
        :meth:`~circleguard.loadables.Replay.keydowns` for more details.
    t: ndarray[int]
        A 1d array containing the timestamp for each frame.
        |br|
        This is only nonnull after the replay has been loaded.
    xy: ndarray[float]
        A 2d, two column array, containing the ``x`` and ``y`` coordinates of
        each frame in the first and second column respectively.
        |br|
        This is only nonnull after the replay has been loaded.
    k: ndarray[int]
        A 1d array containing the keys pressed for each frame.
        |br|
        This is only nonnull after the replay has been loaded.
    """
    def __init__(self, weight, cache):
        super().__init__(cache)
        self.weight = weight

        # These attributes might or might not be set once the replay loads.
        # Ideally, a replay would provide all of these attributes, but there are
        # some cases when only a subset is available.
        #
        # If only some of these attributes are set after the replay is loaded,
        # some ``Circleguard`` methods may reject this replay, as it does not
        # contain the information necessary to do whatever the method needs to.
        #
        # For instance, if the replay provides ``replay_data`` but not ``mods``,
        # ``Circleguard#similarity`` will reject it, as we will not know whether
        # whether ``Mod.HR`` was enabled on the replay, and thus whether to flip
        # the replay before comparing it to another one.

        # replays have no information about their game version by default.
        # Subclasses might set this if they have more information to provide
        # about their version, whether on instantiation or after being loaded.
        self.game_version = NoGameVersion()
        self.timestamp    = None
        # declared as a property with a getter and setter so we can set
        # map_info's map_id attribute automatically
        self._beatmap_id       = None
        # replays have no information about their map by default.
        # TODO: remove in core 6.0.0, in favor of ``Replay#map_available`` (and
        # possibly other mechanisms).
        self.map_info         = MapInfo()
        self.username         = None
        self.user_id          = None
        self.mods             = None
        self.replay_id        = None
        self.replay_data      = None
        self.replay_hash      = None
        self.count_300        = None
        self.count_100        = None
        self.count_50         = None
        self.count_geki       = None
        self.count_katu       = None
        self.count_miss       = None
        self.score            = None
        self.max_combo        = None
        self.is_perfect_combo = None
        self.life_bar_graph   = None
        self.rng_seed         = None
        self.pp               = None

        # These attributes remain ``None``` when replay is unloaded, or loaded
        # but with no data.
        self.t            = None
        self.xy           = None
        self.k            = None
        self._keydowns    = None

    def beatmap_available(self, _library):
        return bool(self.beatmap_id)

    # TODO remove in core 6.0.0
    map_available = beatmap_available

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

    def beatmap(self, library):
        """
        The beatmap this replay was played on.

        Parameters
        ----------
        library: :class:`slider.library.Library`
            The library used by the calling
            :class:`~circleguard.circleguard.Circleguard` instance. Beatmaps
            which have already been downloaded and are cached in this library
            may be returned here instead of redownloading them.
            |br|
            Beatmaps which we download or create in this method, but were not
            previously stored in the library, may also be stored into the
            library for future use as a result of calling this method.

        Returns
        -------
        :class:`slider.beatmap.Beatmap`
            The beatmap this replay was played on.
        None
            If we do not know what beatmap this replay was played on.
        """
        if not self.beatmap_available(library):
            return None

        return library.lookup_by_id(self.beatmap_id, download=True, save=True)

    def _process_replay_data(self, replay_data):
        """
        Preprocesses the replay data (turns it into numpy arrays) for fast
        manipulation when investigating.

        Paramters
        ---------
        replay_data: list[:class:`~osrparse.Replay.ReplayEvent`]
            A list of :class:`~osrparse.Replay.ReplayEvent` objects,
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

        # In rare cases (I'm not quite sure how to reproduce), a replay's replay
        # data can be empty. We check this here to throw a clearer error
        # message than the IndexError we will get shortly after with
        # ``replay_data[0]``.
        #
        # Note that there's an important distinction between ``replay_data``
        # being ``None`` and being the empty list ``[]`` - the former means the
        # api (or osr, or some other source) had no replay data for this replay,
        # and the latter means it *had* replay data, it was just empty replay
        # data.
        #
        # It might be okay to just return as with the ``replay_data is None``
        # case, but I'm erring on the side of caution and throwing for now.
        #
        # See https://github.com/circleguard/circleguard/issues/133 for examples
        # of replays exhibiting this behavior.
        if replay_data == []:
            raise ValueError("This replay's replay data was empty. This should "
                "not happen and is indicative of a misbehaved replay.")

        # TODO we'll want to add proper support for non-std replays at some
        # point, but for now we'll just drop the replay data and early return.
        # This results in identical behavior with previous versions of
        # circlecore, before osrparse supported non-std gamemodes.
        if not isinstance(replay_data[0], ReplayEventOsu):
            self.replay_data = None
            return

        # remove invalid zero time frame at beginning of replay
        # https://github.com/ppy/osu/blob/1587d4b26fbad691242544a62dbf017a78705
        # ae3/osu.Game/Scoring/Legacy/LegacyScoreDecoder.cs#L242-L245
        if replay_data[0].time_delta == 0:
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
        running_t = next(replay_data).time_delta
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

            e_t = e.time_delta
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

                data[3].append(last_positive_frame.keys)

            data[0].append(running_t)
            data[1].append(e.x)
            data[2].append(e.y)
            # TODO: are we taking a performance hit here by letting osrparse
            # convert keys to an enum in its replay's init, then converting it
            # back to an int here (since it's faster for us to work with raw
            # ints)?
            # We could add a ``fast_parse`` option to osrparse which doesn't
            # use nice things like enums if this turns out to be a performance
            # issue.
            data[3].append(int(e.keys))
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
    def beatmap_id(self):
        return self._beatmap_id

    @beatmap_id.setter
    def beatmap_id(self, beatmap_id):
        self._beatmap_id = beatmap_id
        self.map_info.map_id = beatmap_id

    # TODO remove in core 6.0.0
    @property
    def map_id(self):
        return self._beatmap_id

    @map_id.setter
    def map_id(self, beatmap_id):
        self._beatmap_id = beatmap_id
        self.map_info.map_id = beatmap_id

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
        return (f"Replay(timestamp={self.timestamp},"
            f"beatmap_id={self.beatmap_id},user_id={self.user_id},"
            f"mods={self.mods},replay_id={self.replay_id},weight={self.weight},"
            f"loaded={self.loaded},username={self.username})")

    def __str__(self):
        return f"Replay by {self.username} on {self.beatmap_id}"


class ReplayMap(Replay):
    """
    A :class:`~.Replay` that was submitted to online servers.

    Parameters
    ----------
    map_id: int
        The id of the map the replay was played on.
    user_id: int
        The id of the player who played the replay.
    mods: :class:`~circleguard.mod.ModCombination`
        The mods the replay was played with. If ``None``, the
        highest scoring replay of ``user_id`` on ``map_id`` will be loaded,
        regardless of mod combination. Otherwise, the replay with ``mods``
        will be loaded.
    cache: bool
        Whether to cache this replay once it is loaded.

    Notes
    -----
    The following replay-related attributes are available (not ``None``) when
    this replay is unloaded:

    * beatmap_id
    * user_id
    * mods (if passed)

    In addition to the above, the following replay-related attributes are
    available (not ``None``) when this replay is loaded:

    * timestamp
    * username
    * mods
    * replay_id
    * count_300
    * count_100
    * count_50
    * count_geki
    * count_katu
    * count_miss
    * score
    * max_combo
    * is_perfect_combo
    * pp
    * replay_data
    """

    def __init__(self, beatmap_id, user_id, mods=None, cache=None, info=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.log = logging.getLogger(__name__ + ".ReplayMap")
        self.beatmap_id = beatmap_id
        self.user_id = user_id
        self.mods = mods
        self.info = info
        if info:
            self.timestamp = info.date
            self.beatmap_id = info.beatmap_id
            self.user_id = info.user_id
            self.username = info.username
            self.replay_id = info.replay_id
            self.mods = info.mods

        # TODO remove in core 6.0.0
        self.map_id = self.beatmap_id

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
        """
        # only listen to the parent's cache if ours is not set. Lower takes
        # precedence
        cache = cache if self.cache is None else self.cache
        self.log.debug("Loading %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        if not loader:
            raise ValueError("A ReplayMap cannot be loaded without api access")

        if self.info:
            info = self.info
        else:
            info = loader.replay_info(self.beatmap_id, user_id=self.user_id,
                mods=self.mods)

        self.timestamp = info.date
        # estimate version with timestamp, this is only accurate if the user
        # keeps their game up to date
        self.game_version = GameVersion.from_datetime(self.timestamp,
            concrete=False)
        self.username = info.username
        self.mods = info.mods
        self.replay_id = info.replay_id
        self.count_100 = info.count_100
        self.count_300 = info.count_300
        self.count_50 = info.count_50
        self.count_geki = info.count_geki
        self.count_katu = info.count_katu
        self.count_miss = info.count_miss
        self.score = info.score
        self.max_combo = info.max_combo
        self.is_perfect_combo = info.perfect
        self.pp = info.pp

        replay_data = loader.replay_data(info, cache=cache)
        self._process_replay_data(replay_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    def __eq__(self, loadable):
        """
        Whether the two replay maps are equal.

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
        return (self.beatmap_id == loadable.beatmap_id and
            self.user_id == loadable.user_id and self.mods == loadable.mods)

    def __hash__(self):
        return hash((self.beatmap_id, self.user_id, self.mods))

    def __repr__(self):
        if self.loaded:
            return (f"ReplayMap(timestamp={self.timestamp},"
            f"beatmap_id={self.beatmap_id},user_id={self.user_id},"
            f"mods={self.mods},cache={self.cache},replay_id={self.replay_id},"
            f"loaded={self.loaded},username={self.username})")
        return (f"ReplayMap(beatmap_id={self.beatmap_id},"
            f"user_id={self.user_id},mods={self.mods},cache={self.cache},"
            f"loaded={self.loaded})")

    def __str__(self):
        return (f"{'Loaded' if self.loaded else 'Unloaded'} ReplayMap by "
            f"{self.user_id} on {self.beatmap_id}")


class ReplayDataOSR(Replay):
    """
    A :class:`~.Replay` which has been saved in the osr format.

    Parameters
    ----------
    weight: :class:`~circleguard.utils.RatelimitWeight`
        How much it 'costs' to load this replay from the api.
    cache: bool
        Whether to cache this replay once it is loaded.

    Notes
    -----
    ReplayDataStrings have no replay-related attributes available (not ``None``)
    when they are unloaded.

    The following replay-related attributes are available (not ``None``) when
    this replay is loaded:

    * timestamp
    * beatmap_id
    * username
    * user_id
    * mods
    * replay_id
    * beatmap_hash
    * replay_hash
    * count_300
    * count_100
    * count_50
    * count_geki
    * count_katu
    * count_miss
    * score
    * max_combo
    * is_perfect_combo
    * life_bar_graph (currently unparsed)
    * replay_data
    """
    def __init__(self, ratelimit_weight, cache=None):
        super().__init__(ratelimit_weight, cache)
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.beatmap_hash = None

        self._user_id_func = None
        self._user_id = None
        self._beatmap_id_func = None

    def beatmap(self, library):
        if not self.beatmap_available(library):
            return None
        # if we can't load our beatmap_id, fall back to loading from slider.
        if not self.can_load_api_attributes() and self.beatmap_hash:
            return library.lookup_by_md5(self.beatmap_hash)
        return super().beatmap(library)

    def beatmap_available(self, library):
        beatmap_cached = library.beatmap_cached(beatmap_md5=self.beatmap_hash)
        if self.beatmap_hash and beatmap_cached:
            return True
        return super().beatmap_available(library)

    def load_from_osrparse_replay(self, replay, loader, _cache):
        """
        Loads the data for this replay from the already loaded osrparse replay.

        Parameters
        ----------
        loader: :class:`~.loader.Loader`
            The :class:`~.loader.Loader` to load this replay with.
            |br|
            If ``None``, this replay will be unable to retrieve its ``map_id``
            or ``user_id``, but everything else will still be loaded.
        cache: bool
            Whether to cache this replay after loading it. This only has an
            effect if ``self.cache`` is unset (``None``). Note that currently
            we do not cache :class:`~.ReplayPath` regardless of this parameter.
        """
        self.game_version = GameVersion(replay.game_version, concrete=True)
        self.beatmap_hash = replay.beatmap_hash
        self.username = replay.username
        self.replay_hash = replay.replay_hash
        self.count_300 = replay.count_300
        self.count_100 = replay.count_100
        self.count_50 = replay.count_50
        self.count_geki = replay.count_geki
        self.count_katu = replay.count_katu
        self.count_miss = replay.count_miss
        self.score = replay.score
        self.max_combo = replay.max_combo
        self.is_perfect_combo = replay.perfect
        self.mods = Mod(replay.mods.value)
        self.life_bar_graph = replay.life_bar_graph
        self.timestamp = replay.timestamp
        self.replay_id = replay.replay_id
        self.rng_seed = replay.rng_seed

        if loader:
            self._user_id_func = loader.user_id
            self._beatmap_id_func = loader.beatmap_id

        self._process_replay_data(replay.replay_data)
        self.loaded = True
        self.log.log(TRACE, "Finished loading %s", self)

    def load_from_file(self, path, loader, cache):
        replay = osrparse.Replay.from_path(path)
        self.load_from_osrparse_replay(replay, loader, cache)

    def load_from_string(self, replay_data_str, loader, cache):
        replay = osrparse.Replay.from_string(replay_data_str)
        self.load_from_osrparse_replay(replay, loader, cache)


    @property
    def user_id(self):
        if not self.loaded:
            return None
        if not self._user_id_func:
            raise ValueError("The map if of a replay which has been loaded "
                "without a ``Loader`` cannot be retrieved.")
        if not self._user_id:
            self._user_id = self._user_id_func(self.username)
        return self._user_id

    @property
    def beatmap_id(self):
        if not self.loaded:
            return None
        if not self._beatmap_id_func:
            raise ValueError("The map id of a replay which has been loaded "
                "without a ``Loader`` cannot be retrieved. This can happen if "
                "the replay was loaded with a ``KeylessCircleguard``.")
        # property inheritence is a bit nasty. See
        # https://stackoverflow.com/a/37663266 for reference
        if not super().beatmap_id:
            beatmap_id = self._beatmap_id_func(self.beatmap_hash)
            super(ReplayDataOSR, self.__class__).beatmap_id.fset(self,
                beatmap_id)
        return super().beatmap_id

    @beatmap_id.setter
    def beatmap_id(self, beatmap_id):
        super(ReplayDataOSR, self.__class__).beatmap_id.fset(self, beatmap_id)

    # TODO remove in core 6.0.0
    @property
    def map_id(self):
        if not self.loaded:
            return None
        if not self._beatmap_id_func:
            raise ValueError("The map id of a replay which has been loaded "
                "without a ``Loader`` cannot be retrieved. This can happen if "
                "the replay was loaded with a ``KeylessCircleguard``.")
        if not super().beatmap_id:
            beatmap_id = self._beatmap_id_func(self.beatmap_hash)
            super(ReplayDataOSR, self.__class__).beatmap_id.fset(self,
                beatmap_id)
        return super().beatmap_id

    @map_id.setter
    def map_id(self, map_id):
        super(ReplayDataOSR, self.__class__).map_id.fset(self, map_id)

    def can_load_api_attributes(self):
        """
        Whether we can load attributes that are lazy loaded and require api
        calls, such as ``map_id`` or ``user_id``, if requested.
        """
        return bool(self._beatmap_id_func) and bool(self._user_id_func)

    def api_attributes_loaded(self):
        """
        Whether attributes that are lazy loaded and require api calls, such as
        ``map_id`` or ``user_id``, have already been loaded.
        """
        return bool(self._beatmap_id) and bool(self._user_id)


    @user_id.setter
    def user_id(self, user_id):
        self._user_id = user_id


class ReplayPath(ReplayDataOSR):
    """
    A :class:`~.Replay` saved locally in a ``.osr`` file.

    Parameters
    ----------
    path: str or :class:`os.PathLike`
        The path to the replay file.
    cache: bool
        Whether to cache this replay once it is loaded. Note that currently
        we do not cache :class:`~.ReplayPath` regardless of this parameter.

    Notes
    -----
    ReplayPaths have no replay-related attributes available (not ``None``) when
    they are unloaded.

    The following replay-related attributes are available (not ``None``) when
    this replay is loaded:

    * timestamp
    * beatmap_id
    * username
    * user_id
    * mods
    * replay_id
    * beatmap_hash
    * replay_hash
    * count_300
    * count_100
    * count_50
    * count_geki
    * count_katu
    * count_miss
    * score
    * max_combo
    * is_perfect_combo
    * life_bar_graph (currently unparsed)
    * replay_data
    """

    def __init__(self, path, cache=None):
        super().__init__(RatelimitWeight.LIGHT, cache)
        self.log = logging.getLogger(__name__ + ".ReplayPath")
        self.path = Path(path).absolute()
        self.beatmap_hash = None

        self._user_id_func = None
        self._user_id = None
        self._beatmap_id_func = None

    def load(self, loader, cache):
        self.log.debug("Loading ReplayPath %r", self)
        if self.loaded:
            self.log.debug("%s already loaded, not loading", self)
            return

        self.load_from_file(self.path, loader, cache)

    def __eq__(self, loadable):
        """
        Whether these replay paths are equal.

        Notes
        -----
        If one or both replay paths don't have replay data, this checks path
        equality. If both replay paths have replay data, this checks the
        equality of their replay data.
        |br|
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
            api_attrs_string = ","
            # avoid loading these lazy-loaded attributes by accessing them here,
            # unless they're already loaded
            if self.api_attributes_loaded():
                api_attrs_string = (f"beatmap_id={self.beatmap_id},"
                    f"user_id={self.user_id},")
            return (f"ReplayPath(path={self.path},{api_attrs_string}"
                f"mods={self.mods},replay_id={self.replay_id},"
                f"weight={self.weight},loaded={self.loaded},"
                f"username={self.username})")
        return (f"ReplayPath(path={self.path},weight={self.weight},"
                f"loaded={self.loaded})")

    def __str__(self):
        if self.loaded:
            return (f"Loaded ReplayPath by {self.username} on "
                f"{self.beatmap_id} at {self.path}")
        return f"Unloaded ReplayPath at {self.path}"


class ReplayString(ReplayDataOSR):
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

    Notes
    -----
    ReplayPaths have no replay-related attributes available (not ``None``) when
    they are unloaded.

    The following replay-related attributes are available (not ``None``) when
    this replay is loaded:

    * timestamp
    * beatmap_id
    * username
    * user_id
    * mods
    * replay_id
    * beatmap_hash
    * replay_hash
    * count_300
    * count_100
    * count_50
    * count_geki
    * count_katu
    * count_miss
    * score
    * max_combo
    * is_perfect_combo
    * life_bar_graph (currently unparsed)
    * replay_data

    Examples
    --------
    >>> replay_data = open("replay.osr", "rb").read()
    >>> r = ReplayString(replay_data)
    >>> cg.load(r)
    >>> print(cg.ur(r))
    """

    def __init__(self, replay_data_str, cache=None):
        super().__init__(RatelimitWeight.LIGHT, cache)
        self.log = logging.getLogger(__name__ + ".ReplayString")
        self.replay_data_str = replay_data_str

    def load(self, loader, cache):
        if self.loaded:
            return
        self.load_from_string(self.replay_data_str, loader, cache)

    def __eq__(self, loadable):
        if not isinstance(loadable, ReplayString):
            return False
        return self.replay_data_str == loadable.replay_data_str

    def __hash__(self):
        return hash(self.replay_data_str)

    def __repr__(self):
        if self.loaded:
            api_attrs_string = ","
            if self.api_attributes_loaded():
                api_attrs_string = (f"beatmap_id={self.beatmap_id},"
                    f"user_id={self.user_id},")
            return (f"ReplayString(len(replay_data_str)="
                f"{len(self.replay_data_str)},{api_attrs_string}"
                f"mods={self.mods},"
                f"replay_id={self.replay_id},weight={self.weight},"
                f"loaded={self.loaded},username={self.username})")
        return f"ReplayString(len(replay_data_str)={len(self.replay_data_str)})"

    def __str__(self):
        if self.loaded:
            return (f"Loaded ReplayString by {self.username} on "
                f"{self.beatmap_id}")
        return (f"Unloaded ReplayString with {len(self.replay_data_str)} "
            "chars of data")


class ReplayID(Replay):
    """
    A :class:`~.Replay` that was submitted online and is represented by a unique
    replay id.

    Parameters
    ----------
    replay_id: int
        The id of the replay.
    cache: bool
        Whether to cache this replay once it is loaded. Note that we currently
        do not cache ReplayIDs.

    Notes
    -----
    The following replay-related attributes are available (not ``None``) when
    this replay is unloaded:

    * replay_id

    In addition to the above, the following replay-related attributes are
    available (not ``None``) when this replay is loaded:

    * replay_data
    """
    def __init__(self, replay_id, cache=None):
        super().__init__(RatelimitWeight.HEAVY, cache)
        self.replay_id = replay_id

    def load(self, loader, cache):
        if self.loaded:
            return
        if not loader:
            raise ValueError("A ReplayID cannot be loaded without api access")
        # TODO file github issue about loading info from replay id, right now we
        # can literally only load the replay data which isn't that useful
        cache = cache if self.cache is None else self.cache
        replay_data = loader.replay_data_from_id(self.replay_id, cache)
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        return self.replay_id == other.replay_id

    def __hash__(self):
        return hash(self.replay_id)


class CachedReplay(Replay):
    """
    This class is intended to be instantiated from
    :func:`~.ReplayCache.load_info` and should not be instantiated manually.
    """
    def __init__(self, user_id, beatmap_id, mods, replay_data, replay_id):
        super().__init__(RatelimitWeight.NONE, False)
        self.user_id = user_id
        self.beatmap_id = beatmap_id
        self.mods = Mod(mods)
        self.replay_data = replay_data
        self.replay_id = replay_id

        # TODO remove in core 6.0.0
        self.map_id = beatmap_id

    def load(self, loader, cache):
        if self.loaded:
            return
        decompressed = wtc.decompress(self.replay_data)
        replay_data = osrparse.parse_replay_data(decompressed, decoded=True)
        self._process_replay_data(replay_data)
        self.loaded = True

    def __eq__(self, other):
        return self.replay_id == other.replay_id

    def __hash__(self):
        return hash(self.replay_id)

class ReplayOssapi(ReplayDataOSR):
    """
    Converts a :module:`ossapi` replay to a circlecore :class:`~.Replay`.
    Requires ossapi to be installed (you can't get an ossapi replay without
    having ossapi installed anyway).
    """

    def __init__(self, ossapi_replay):
        super().__init__(RatelimitWeight.NONE, False)

        import ossapi
        game_mode_map = {
            ossapi.GameMode.OSU:    osrparse.GameMode.STD,
            ossapi.GameMode.TAIKO:  osrparse.GameMode.TAIKO,
            ossapi.GameMode.CATCH:  osrparse.GameMode.CTB,
            ossapi.GameMode.MANIA:  osrparse.GameMode.MANIA,
        }

        # an ossapi replay is almost identical to an osrparse replay, except
        # it has a different gamemode and mod enum.
        self.osrparse_replay = osrparse.Replay(
            game_mode_map[ossapi_replay.mode],
            ossapi_replay.game_version,
            ossapi_replay.beatmap_hash,
            ossapi_replay.username,
            ossapi_replay.replay_hash,
            ossapi_replay.count_300,
            ossapi_replay.count_100,
            ossapi_replay.count_50,
            ossapi_replay.count_geki,
            ossapi_replay.count_katu,
            ossapi_replay.count_miss,
            ossapi_replay.score,
            ossapi_replay.max_combo,
            ossapi_replay.perfect,
            osrparse.Mod(ossapi_replay.mods.value),
            ossapi_replay.life_bar_graph,
            ossapi_replay.timestamp,
            ossapi_replay.replay_data,
            ossapi_replay.replay_id,
            ossapi_replay.rng_seed,
        )

    def load(self, loader, cache):
        if self.loaded:
            return

        self.load_from_osrparse_replay(self.osrparse_replay, loader, cache)

    def __eq__(self, loadable):
        if not isinstance(loadable, ReplayOssapi):
            return False
        return self.osrparse_replay == loadable.osrparse_replay

    def __hash__(self):
        return hash(self.osrparse_replay)

    def __str__(self):
        if self.loaded:
            return (f"Loaded ReplayOssapi by {self.username} on "
                f"{self.beatmap_id}")
        return (f"Unloaded ReplayOssapi by {len(self.username)} on beatmap "
            f"hash {self.beatmap_hash}")
