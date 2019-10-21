from pathlib import Path
import sys
import itertools
import os
from os.path import isfile, join
import logging
from tempfile import TemporaryDirectory

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard.exceptions import CircleguardException
from circleguard.replay import Check, ReplayMap, ReplayPath, Replay, Map
from circleguard.enums import Detect, RatelimitWeight
from slider import Beatmap, Library


class Circleguard:
    """
    Circleguard compares and investigates replays to detect cheats.

    Circleguard provides convenience methods for common use cases: map_check, verify, user_check, and local_check -
    see each method for further documentation. If these convenience methods are not flexible enough for you, you can instantiate
    a Check and call circleguard.run(check).

    Under the hood, convenience methods simply instantiate a Check object and call circleguard#run(check). The run method
    returns a generator containing Result objects, which contains the result of each comparison of the replays. See the
    Result class for further documentation.
    """


    def __init__(self, key, db_path=None, slider_dir=None, loader=None, cache=True):
        """
        Initializes a Circleguard instance.

        Args:
            String key: An osu API key.
            [Path or String] db_path: A pathlike object to the databsae file to write and/or read cached replays.
                    If the given file doesn't exist, a fresh database if created. If this is not passed,
                    no replays will be cached or loaded from cache.
            [Path or String] slider_dir: A pathlike object to the directory used by slider to store beatmaps. If None,
                    a temporary directory will be created, and destroyed when this circleguard object is garbage collected.
            Class loader: a subclass of circleguard.Loader, which will be used in place of circleguard.Loader if passed.
                    Instantiated with two args - a key and cacher.
            bool cache: if passed without db_path, has no effect. If db_path is passed and cache is True,
                    replays will be loaded from and stored to the db. If cache is False, replays will be loaded from the db but not stored.
        """

        self.cacher = None
        if db_path is not None:
            # allows for . to be passed to db_path
            db_path = Path(db_path).absolute()
            # they can set cache to False later with:func:`~.circleguard.set_options`
            # if they want; assume caching is desired if db path is passed
            self.cacher = Cacher(cache, db_path)

        self.log = logging.getLogger(__name__)
        # allow for people to pass their own loader implementation/subclass
        self.loader = Loader(key, cacher=self.cacher) if loader is None else loader(key, self.cacher)
        if slider_dir is None:
            # have to keep a reference to it or the folder gets deleted and can't be walked by Library
            self.__slider_dir = TemporaryDirectory()
            self.library = Library(self.__slider_dir.name)
        else:
            self.library = Library(slider_dir)


    def run(self, check):
        """
        Compares and investigates replays in the check for cheats.

        Args:
            Check check: The check with replays to look at.

        Returns:
            A generator containing Result objects of the comparisons and investigations.
        """

        c = check
        self.log.info("Running circleguard with %r", c)

        c.load(self.loader)
        d = c.detect
        # steal check
        if Detect.STEAL in d:
            compare1 = c.all_replays()
            compare2 = c.all_replays2()
            comparer = Comparer(d.steal_thresh, compare1, replays2=compare2)
            yield from comparer.compare()

        # relax check
        if Detect.RELAX in d:
            for replay in c.all_replays():
                bm = self.library.lookup_by_id(replay.map_id, download=True, save=True)
                investigator = Investigator(replay, bm, d.ur_thresh)
                yield from investigator.investigate()

    def load(self, loadable):
        """
        Loads the given loadable. This is identical to calling loadable.load(cg.loader).
        """
        loadable.load(self.loader)

    def load_info(self, container):
        """
        Loads the given ReplayContainer. This is identical to calling container.load_info(cg.loader).
        """
        container.load_info(self.loader)


    def set_options(self, cache=None):
        """
        Changes the default value for different options in circleguard.
        Affects only the ircleguard instance this method is called on.

        Args:
            Boolean cache: Whether to cache the loaded loadables. Defaults to False, or the config value if changed.
                           If no database file was passed, this value has no effect, as loadables will not be cached.
            Integer loglevel: What level to log at. Circlecore follows standard python logging levels, with an added level of
                          TRACE with a value of 5 (lower than debug, which is 10). The value passed to loglevel is
                          passed directly to the setLevel function of this instance's logger. WARNING by default.
                          For more information on log levels, see the standard python logging lib.
        """

        # remnant code from when we had many options available in set_options. Left in for easy future expansion
        for k, v in locals().items():
            if v is None or k == "self":
                continue
            if k == "cache":
                self.cache = cache
                self.cacher.should_cache = cache
                continue

def set_options(loglevel=None):
    """
    Set global options for circlecore.

    Attributes
    ----------
    logevel: int
        What level to log at. Circlecore follows standard python logging
        levels, with an added level of TRACE with a value of 5 (lower than
        debug, which is 10). The value passed to loglevel is passed directly to
        the setLevel function of the circleguard root logger. WARNING by
        default. For more information on log levels, see the standard python
        logging lib.
    """
    if loglevel is not None:
        logging.getLogger("circleguard").setLevel(loglevel)
