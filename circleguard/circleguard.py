from pathlib import Path
import sys
import itertools
import os
from os.path import isfile, join
import logging

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard import config
from circleguard.exceptions import CircleguardException
from circleguard.replay import Check, ReplayMap, ReplayPath
from circleguard.enums import Detect, RatelimitWeight


class Circleguard:
    """
    Circleguard compares and investigates replays to detect cheats.

    Circleguard provides convenience methods for common use cases: map_check, verify, user_check, and local_check -
    see each method for further documentation. If these convenience methods are not flexible enough for you, you will
    have to instantiate your own Check object and call circleguard#run(check).

    Under the hood, convenience methods simply instantiate a Check object and call circleguard#run(check). The run method
    returns a generator containing Result objects, which contains the result of each comparison of the replays. See the
    Result class for further documentation.
    """

    # used to distinguish log output for cg instances
    NUM = 1

    def __init__(self, key, db_path, loader=None):
        """
        Initializes a Circleguard instance.

        Args:
            String key: An osu API key.
            [Path or String] db_path: A pathlike object to the databse file to write and/or read cached replays.
        """

        self.log = logging.getLogger(__name__ + str(Circleguard.NUM))
        self.db_path = Path(db_path).absolute() # allows for . to be passed to db_path
        cacher = Cacher(config.cache, self.db_path)
        # allow for people to pass their own loader implementation/subclass
        self.loader = Loader(cacher, key) if loader is None else loader(cacher, key)
        self.options = Options()
        Circleguard.NUM += 1

    def run(self, check):
        """
        Compares replays contained in the check object for replay steals.

        Args:
            Check check: A Check object containing either one or two sets of replays. If it was initialized with
                         a single replay set, all replays in that set are compared with each other. If it was
                         initialized with two replay sets, all replays in the first set are compared with all
                         replays in the second set.

        Returns:
            A generator containing Result objects of the comparisons.
        """

        self.log.info("Running circleguard with a Check")

        check.filter()
        # steal check
        compare1 = [replay for replay in check.replays if replay.detect & Detect.STEAL]
        compare2 = [replay for replay in check.replays2 if replay.detect & Detect.STEAL]
        num_to_load = len([replay for replay in compare1 + compare2 if replay.weight == RatelimitWeight.HEAVY])

        self.loader.new_session(num_to_load)
        check.load(self.loader)
        # all replays now have replay data, above is where ratelimit waiting would occur
        comparer = Comparer(check.thresh, compare1, replays2=compare2)
        yield from comparer.compare(mode=check.mode)

        # relax check (TODO)

    def map_check(self, map_id, u=None, num=None, cache=None, thresh=None, include=None):
        """
        Checks a map's leaderboard for replay steals.

        Args:
            Integer map_id: The id of the map (not the id of the mapset!) to compare replays from.
            Integer u: A user id. If passed, only the replay made by this user id on the given map will be
                       compared with the rest of the lederboard of the map. No other comparisons will be made.
            Integer num: The number of replays to compare from the map. Defaults to 50, or the config value if changed.
                         Loads from the top ranks of the leaderboard, so num=20 will compare the top 20 scores. This
                         number must be between 1 and 100, as restricted by the osu api.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                              The include function will be passed a single argument - the circleguard.Replay object, or one
                              of its subclasses.

        Returns:
            A generator containing Result objects of the comparisons.
        """
        check = self.create_map_check(map_id, u, num, cache, thresh, include)
        yield from self.run(check)


    def create_map_check(self, map_id, u=None, num=None, cache=None, thresh=None, include=None):
        """
        Creates the Check object used in the map_check convenience method. See that method for more information.
        """
        options = self.options
        num = num if num else options.num
        cache = cache if cache else options.cache
        thresh = thresh if thresh else options.thresh
        include = include if include else options.include

        self.log.info("Map check with map id %d, u %s, num %s, cache %s, thresh %s", map_id, u, num, cache, thresh)
        replays2 = None
        if u:
            info = self.loader.user_info(map_id, user_id=u)
            replays2 = [ReplayMap(info.map_id, info.user_id, info.mods, username=info.username)]
        infos = self.loader.user_info(map_id, num=num)
        replays = [ReplayMap(info.map_id, info.user_id, info.mods, username=info.username) for info in infos]
        return Check(replays, replays2=replays2, cache=cache, thresh=thresh, include=include)

    def verify(self, map_id, u1, u2, cache=None, thresh=None, include=None):
        """
        Verifies that two user's replay on a map are steals of each other.

        Args:
            Integer map_id: The id of the map to compare replays from.
            Integer u1: The user id of one of the users who set a replay on this map.
            Integer u2: The user id of the second user who set a replay on this map.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                              The include function will be passed a single argument - the circleguard.Replay object, or one
                              of its subclasses.

        Returns:
            A generator containing Result objects of the comparisons.
        """

        check = self.create_verify_check(map_id, u1, u2, cache, thresh, include)
        yield from self.run(check)

    def create_verify_check(self, map_id, u1, u2, cache=None, thresh=None, include=None):
        """
        Creates the Check object used in the verify_check convenience method. See that method for more information.
        """
        options = self.options
        cache = cache if cache else options.cache
        thresh = thresh if thresh else options.thresh
        include = include if include else options.include

        self.log.info("Verify with map id %d, u1 %s, u2 %s, cache %s", map_id, u1, u2, cache)
        info1 = self.loader.user_info(map_id, user_id=u1)
        info2 = self.loader.user_info(map_id, user_id=u2)
        replay1 = ReplayMap(info1.map_id, info1.user_id, info1.mods, username=info1.username)
        replay2 = ReplayMap(info2.map_id, info2.user_id, info2.mods, username=info2.username)

        return Check([replay1, replay2], cache=cache, thresh=thresh, include=include)

    def user_check(self, u, num, cache=None, thresh=None, include=None):
        """
        Checks a user's top plays for replay steals.

        For each of the user's top plays, the replay will be compared to the top plays of the map,
        then compared to all the user's other plays on the map, to check for both stealing and remodding.

        If a user has no or only one downloadable replay on the map, no comparisons to the user's other plays are made.
        Obviously, if the play is not downloadable, no comparison is made against the map leaderboard for that replay either.

        Args:
            Integer u: The user id of the user to check
            Integer num: The number of replays of each map to compare against the user's replay. For now, this also serves as the
                         number of top plays of the user to check for replay stealing and remodding.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                              The include function will be passed a single argument - the circleguard.Replay object, or one
                              of its subclasses.

        Returns:
            A generator containing Result objects of the comparisons.
        """

        for check_list in self.create_user_check(u, num, cache, thresh, include):
            # yuck; each top play has two different checks (remodding and stealing)
            # which is why we need a double loop
            for check in check_list:
                yield from self.run(check)

    def create_user_check(self, u, num_top, num_users, cache=None, thresh=None, include=None):
        """
        Creates the Check object used in the user_check convenience method. See that method for more information.

        Bewarned that this method does not return a single Check object like all other circleguard#create methods.
        Instead it returns a list of lists of Check objects [[Check, Check], [Check, Check], ...], because each top
        play of the user needs two Check objects, one for replay stealing and one for remodding. Be sure to handle
        this special case accordingly.
        """
        options = self.options
        cache = cache if cache else options.cache
        thresh = thresh if thresh else options.thresh
        include = include if include else options.include

        self.log.info("User check with u %s, num_top %s, num_users %s", u, num_top, num_users)
        ret = []
        for map_id in self.loader.get_user_best(u, num_top):
            info = self.loader.user_info(map_id, user_id=u)
            if not info.replay_available:
                continue  # if we can't download the user's replay on the map, we have nothing to compare against
            user_replay = [ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username)]

            infos = self.loader.user_info(map_id, num=num_users)
            replays = [ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username) for info in infos]

            remod_replays = []
            for info in self.loader.user_info(map_id, user_id=u, limit=False)[1:]:
                remod_replays.append(ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username))

            check1 = Check(user_replay, replays2=replays, cache=cache, thresh=thresh, include=include)
            check2 = Check(user_replay + remod_replays, cache=cache, thresh=thresh, include=include)
            ret.append([check1, check2])

        return ret


    def local_check(self, folder, map_id=None, u=None, num=None, cache=None, thresh=None, include=None):
        """
        Compares locally stored osr files for replay steals.

        Args:
            [Path or String] folder: A pathlike object to the directory containing osr files.
            Integer map_id: A map id. If passed, the osr files will be compared against the top
                            plays on this map (50 by default).
            Integer u: A user id. If both this and map_id are passed, the osr files will be compared
                       against the user's play on the map. This value has no effect if passed without map_id.
            Integer num: The number of replays to compare from the map. Defaults to 50, or the config value if changed.
                         Loads from the top ranks of the leaderboard, so num=20 will compare the top 20 scores. This
                         number must be between 1 and 100, as restricted by the osu api. This value has no effect
                         if passed with both u and map_id.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                              The include function will be passed a single argument - the circleguard.Replay object, or one
                              of its subclasses.

        Returns:
            A generator containing Result objects of the comparisons.
        """

        check = self.create_local_check(folder, map_id, u, num, cache, thresh, include)
        yield from self.run(check)

    def create_local_check(self, folder, map_id=None, u=None, num=None, cache=None, thresh=None, include=None):
        """
        Creates the Check object used in the local_check convenience method. See that method for more information.
        """
        options = self.options
        num = num if num else options.num
        cache = cache if cache else options.cache
        thresh = thresh if thresh else options.thresh
        include = include if include else options.include

        paths = [folder / f for f in os.listdir(folder) if isfile(folder / f) and f.endswith(".osr")]
        local_replays = [ReplayPath(path) for path in paths]
        online_replays = None
        if map_id:
            if u:
                infos = self.loader.user_info(map_id, user_id=u)
            else:
                # num guaranteed to be defined, either passed or from settings.
                infos = self.loader.user_info(map_id, num=num)

            online_replays = [ReplayMap(info.map_id, info.user_id, info.mods, username=info.username) for info in infos]

        return Check(local_replays, replays2=online_replays, thresh=thresh, include=include)

    def load(self, check, replay):
        """
        Loads the given replay. This is identical to calling replay.load(cg.loader, check.cache) if cg is your
        Circleguard instance and check is your Check instance.. This method exists to emphasize that this behavior is encouraged,
        and tied to a specific cg (and Check) instance. The Check is necessary to inherit the cache setting from the Check
        in case it differs from the Circleguard option (since it is more specific, it would override circleguard). See the
        options documentation for more details on setting inheritence.
        """
        replay.load(self.loader, check.cache)

    def set_options(self, thresh=None, num=None, cache=None, failfast=None, loglevel=None, include=None):
        """
        Changes the default value for different options in circleguard.
        Affects only the ircleguard instance this method is called on.

        Args:
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True. 18 by default.
            Integer num: How many replays to load from a map when doing a map check. 50 by default.
            Boolean cache: Whether downloaded replays should be cached or not. False by default.
            Boolean failfast: Will throw an exception if no comparisons can be made for a given Check object,
                          or silently make no comparisons otherwise. False by default.
            Integer loglevel: What level to log at. Circlecore follows standard python logging levels, with an added level of
                          TRACE with a value of 5 (lower than debug, which is 10). The value passed to loglevel is
                          passed directly to the setLevel function of this instance's logger. WARNING by default.
                          For more information on log levels, see the standard python logging lib.
            Function include: A Predicate function that returns True if the replay should be loaded, and False otherwise.
                          The include function will be passed a single argument - the circleguard.Replay object, or one
                          of its subclasses.
        """

        for k, v in locals().items():
            if v is None or k == "self":
                continue
            if k == "loglevel":
                self.log.setLevel(loglevel)
                continue
            if hasattr(self.options, k):
                setattr(self.options, k, v)
            else:  # this only happens if we fucked up, not the user's fault
                raise CircleguardException(f"The key {k} (value {v}) is not available as a config option for a circleguard instance")

def set_options(thresh=None, num=None, cache=None, failfast=None, loglevel=None, include=None):
    """
    Changes the default value for different options in circleguard.
    Affects all circleguard instances, even ones that have already been instantiated.

    Args:
        Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True. 18 by default.
        Integer num: How many replays to load from a map when doing a map check. 50 by default.
        Boolean cache: Whether downloaded replays should be cached or not. False by default.
        Boolean failfast: Will throw an exception if no comparisons can be made for a given Check object,
                          or silently make no comparisons otherwise. False by default.
        Integer loglevel: What level to log at. Circlecore follows standard python logging levels, with an added level of
                          TRACE with a value of 5 (lower than debug, which is 10). The value passed to loglevel is
                          passed directly to the setLevel function of the circleguard root logger. WARNING by default.
                          For more information on log levels, see the standard python logging lib.
        Function include: A Predicate functrion that returns True if the replay should be loaded, and False otherwise.
                          The include function will be passed a single argument - the circleguard.Replay object, or one
                          of its subclasses.
    """

    for k, v in locals().items():
        if v is None:
            continue
        if k == "loglevel":
            logging.getLogger("circleguard").setLevel(loglevel)
            continue
        if hasattr(config, k):
            setattr(config, k, v)
        else:  # this only happens if we fucked up, not the user's fault
            raise CircleguardException(f"The key {k} (with value {v}) is not available as a config option for global config")



class Options():
    """
    Container class for options, tied to a specific Circleguard instance.
    """

    def __init__(self):
        ...

    # These methods are unfortunately necessary because when
    # config module variables are updated, references to them are not - ie
    # references to config.thresh (or any other) are by value. So, when we
    # access options attributes, just get the latest config variable with these
    # methods.
    @property
    def thresh(self):
        return config.thresh

    @property
    def num(self):
        return config.num

    @property
    def cache(self):
        return config.cache

    @property
    def failfast(self):
        return config.failfast

    @property
    def include(self):
        return config.include
