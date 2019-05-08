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
from circleguard.utils import TRACE, ColoredFormatter


logging.addLevelName(TRACE, "TRACE")
formatter = ColoredFormatter("[%(threadName)s][%(name)s][%(levelname)s]  %(message)s  (%(filename)s:%(lineno)s)")
handler_stream = logging.StreamHandler()
handler_stream.setFormatter(formatter)
logging.getLogger("circleguard").addHandler(handler_stream)


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

    def __init__(self, key, db_path):
        """
        Initializes a Circleguard instance.

        Args:
            String key: An osu API key.
            [Path or String] db_path: A pathlike object to the databse file to write and/or read cached replays.
        """

        self.log = logging.getLogger(__name__)
        self.db_path = Path(db_path)
        cacher = Cacher(config.cache, self.db_path)
        self.loader = Loader(cacher, key)

    def run(self, check):
        """
        Compares replays contained in the check object for replay steals.

        Args:
            Check check: A Check object containing either one or two sets of replays. If it was initialized with
                         a single replay set, all replays in that set are compared with each other. If it was
                         initialized with two replay sets, all replays in the first set are compared with all
                         replays in the second set.
        """

        self.log.info("Running circlegauard with a Check")
        # steal check
        compare1 = [replay for replay in check.replays if replay.detect & Detect.STEAL]
        compare2 = [replay for replay in check.replays2 if replay.detect & Detect.STEAL] if check.replays2 else []
        num_to_load = len([replay for replay in compare1 + compare2 if replay.weight == RatelimitWeight.HEAVY])

        self.loader.new_session(num_to_load)
        check.load(self.loader) # all replays now have replay data, this is where ratelimit waiting would occur
        comparer = Comparer(check.thresh, compare1, replays2=compare2)
        yield from comparer.compare(mode=check.mode)

        # relax check (TODO)

    def map_check(self, map_id, u=None, num=config.num, cache=config.cache, thresh=config.thresh):
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
        """

        self.log.info("Map check with map id %d, u %s, num %s, cache %s, thresh %s", map_id, u, num, cache, thresh)
        replays2 = None
        if u:
            info = self.loader.user_info(map_id, user_id=u)
            replays2 = [ReplayMap(info.map_id, info.user_id, info.mods, username=info.username)]
        infos = self.loader.user_info(map_id, num=num)
        replays = [ReplayMap(info.map_id, info.user_id, info.mods, username=info.username) for info in infos]
        check = Check(replays, replays2=replays2, thresh=thresh)
        yield from self.run(check)

    def verify(self, map_id, u1, u2, cache=config.cache, thresh=config.thresh):
        """
        Verifies that two user's replay on a map are steals of each other.

        Args:
            Integer map_id: The id of the map to compare replays from.
            Integer u1: The user id of one of the users who set a replay on this map.
            Integer u2: The user id of the second user who set a replay on this map.
            Boolean cache: Whether to cache the loaded replays. Defaults to False, or the config value if changed.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
        """

        self.log.info("Verify with map id %d, u1 %s, u2 %s, cache %s", map_id, u1, u2, cache)
        info1 = self.loader.user_info(map_id, user_id=u1)
        info2 = self.loader.user_info(map_id, user_id=u2)
        replay1 = ReplayMap(info1.map_id, info1.user_id, info1.mods, username=info1.username)
        replay2 = ReplayMap(info2.map_id, info2.user_id, info2.mods, username=info2.username)

        check = Check([replay1, replay2], thresh=thresh)
        yield from self.run(check)

    def user_check(self, u, num, thresh=config.thresh):
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
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
        """

        self.log.info("User check with u %s, num %s", u, num)

        for map_id in self.loader.get_user_best(u, num):
            info = self.loader.user_info(map_id, user_id=u)
            if not info.replay_available:
                continue  # if we can't download the user's replay on the map, we have nothing to compare against
            user_replay = [ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username)]

            infos = self.loader.user_info(map_id, num=num)
            replays = [ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username) for info in infos]

            remod_replays = []
            for info in self.loader.user_info(map_id, user_id=u, limit=False)[1:]:
                remod_replays.append(ReplayMap(info.map_id, info.user_id, mods=info.mods, username=info.username))

            yield from self.run(Check(user_replay, replays2=replays, thresh=thresh))

            yield from self.run(Check(user_replay + remod_replays, thresh=thresh))

    def local_check(self, folder, thresh=config.thresh):
        """
        Compares locally stored osr files for replay steals.

        Args:
            [Path or String] folder: A pathlike object to the directory containing osr files.
            Integer thresh: If a comparison scores below this value, its Result object has ischeat set to True.
                            Defaults to 18, or the config value if changed.
        """

        paths = [folder / f for f in os.listdir(folder) if isfile(folder / f) and f.endswith(".osr")]
        replays = [ReplayPath(path) for path in paths]
        check = Check(replays, thresh=thresh)
        yield from self.run(check)


def set_options(thresh=None, num=None, cache=None, failfast=None, loglevel=None):
    """
    Changes the default value for different options in circleguard.

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
    """

    for k, v in locals().items():
        if not v:
            continue
        if k == "loglevel":
            logging.getLogger("circleguard").setLevel(loglevel)
            continue
        if hasattr(config, k):
            setattr(config, k, v)
        else:  # this only happens if we fucked up, not the user's fault
            raise CircleguardException(f"The key {k} (with value {v}) is not available as a config option")
