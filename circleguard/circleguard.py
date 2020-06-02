from pathlib import Path
import sys
import itertools
import os
from os.path import isfile, join
import logging
from tempfile import TemporaryDirectory
from typing import Iterable

from slider import Beatmap, Library

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard.exceptions import CircleguardException
from circleguard.loadable import Check, ReplayMap, ReplayPath, Replay, Map
from circleguard.enums import RatelimitWeight, Detect
from circleguard.result import (Result, StealResult, RelaxResult,
    CorrectionResult, TimewarpResult)


class Circleguard:
    """
    Circleguard investigates replays for cheats.

    Parameters
    ----------
    key: str
        A valid api key. Can be retrieved from https://osu.ppy.sh/p/api/.
    db_path: str or :class:`os.PathLike`
        The path to the database file to read and write cached replays. If the
        path does not exist, a fresh database will be created there.
        If `None`, no replays will be cached or loaded from cache.
    slider_dir: str or :class:`os.PathLike`
        The path to the directory used by :class:`slider.library.Library` to
        store beatmaps. If `None`, a temporary directory will be created for
        :class:`slider.library.Library` and subsequently destroyed when this
        :class:`~Circleguard` object is garbage collected.
    loader: :class:`~circleguard.loader.Loader`
        This loader will be used instead of the base loader if passed.
        This must be the class itself, *not* an instantiation of it. It will be
        with two args - a key and a cacher.
    """
    DEFAULT_ANGLE = 10
    DEFAULT_DISTANCE = 8

    def __init__(self, key, db_path=None, slider_dir=None, loader=None, cache=True):
        self.cache = cache
        self.cacher = None
        if db_path is not None:
            # resolve relative paths
            db_path = Path(db_path).absolute()
            # they can set cache to False later with:func:`~.circleguard.set_options`
            # if they want; assume caching is desired if db path is passed
            self.cacher = Cacher(self.cache, db_path)

        self.log = logging.getLogger(__name__)
        # allow for people to pass their own loader implementation/subclass
        self.loader = Loader(key, cacher=self.cacher) if loader is None else loader(key, self.cacher)
        if slider_dir is None:
            # have to keep a reference to it or the folder gets deleted and can't be walked by Library
            self.slider_dir = TemporaryDirectory()
            self.library = None
        else:
            self.library = Library(slider_dir)


    def run(self, loadables, detect, loadables2=None, max_angle=DEFAULT_ANGLE, min_distance=DEFAULT_DISTANCE)\
        -> Iterable[Result]:
        """
        Investigates loadables for cheats.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to investigate.
        detect: :class:`~.Detect`
            What cheats to investigate for.
        loadables2: list[:class:`~.Loadable`]
            For :data:`~Detect.STEAL`, compare each loadable in ``loadables``
            against each loadable in ``loadables2`` for replay stealing,
            instead of to other loadables in ``loadables``.
        max_angle: float
            For :data:`Detect.CORRECTION`, consider only points (a,b,c) where
            ``∠abc < max_angle``.
        min_distance: float
            For :data:`Detect.CORRECTION`, consider only points (a,b,c) where
            ``|ab| > min_distance`` and ``|bc| > min_distance``.

        Yields
        ------
        :class:`~.Result`
            A result representing an investigation of one or more of the replays
            in ``loadables``, depending on the ``detect`` passed.

        Notes
        -----
        :class:`~.Result`\s are yielded one at a time, as circleguard finishes
        investigating them. This means that you can process results from
        :meth:`~.run` without waiting for all of the investigations to finish.
        """

        c = Check(loadables, self.cache, loadables2=loadables2)
        self.log.info("Running circleguard with check %r", c)

        c.load(self.loader)
        # comparer investigations
        if detect & (Detect.STEAL_SIM | Detect.STEAL_CORR):
            replays1 = c.all_replays1()
            replays2 = c.all_replays2()
            comparer = Comparer(replays1, replays2, detect)
            yield from comparer.compare()

        # investigator investigations
        if detect & (Detect.RELAX | Detect.CORRECTION | Detect.TIMEWARP):
            if detect & Detect.RELAX:
                if not self.library:
                    # connect to library since it's a temporary one
                    library = Library(self.slider_dir.name)
                else:
                    library = self.library

            for replay in c.all_replays():
                bm = None
                # don't download beatmap unless we need it for relax
                if detect & Detect.RELAX:
                    bm = library.lookup_by_id(replay.map_id, download=True, save=True)
                investigator = Investigator(replay, detect, max_angle, min_distance, beatmap=bm)
                yield from investigator.investigate()

            if detect & Detect.RELAX:
                if not self.library:
                    # disconnect from temporary library
                    library.close()

    def steal_check(self, loadables, loadables2=None, method=Detect.STEAL_SIM) -> Iterable[StealResult]:
        """
        Investigates loadables for replay stealing.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to investigate.
        loadables2: list[:class:`~.Loadable`]
            If passed, compare each loadable in ``loadables``
            against each loadable in ``loadables2`` for replay stealing,
            instead of to other loadables in ``loadables``.
        method: :class`~.Detect`
            What method to use to investigate the loadables for replay stealing.
            This should be one of ``Detect.STEAL_SIM`` or ``Detect.STEAL_CORR``,
            or both (or'd together).

        Yields
        ------
        :class:`~.StealResult`
            A result representing a replay stealing investigtion into a pair of
            loadables from ``loadables`` and/or ``loadables2``.
        """
        yield from self.run(loadables, method, loadables2)

    def relax_check(self, loadables) -> Iterable[RelaxResult]:
        """
        Investigates loadables for relax.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to investigate.

        Yields
        ------
        :class:`~.RelaxResult`
            A result representing a relax investigation into a loadable from
            ``loadables``.
        """
        yield from self.run(loadables, Detect.RELAX)

    def correction_check(self, loadables, max_angle=DEFAULT_ANGLE, min_distance=DEFAULT_DISTANCE)\
        -> Iterable[CorrectionResult]:
        """
        Investigates loadables for aim correction.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to investigate.

        Yields
        ------
        :class:`~.CorrectionResult`
            A result representing an aim correction investigation into a
            loadable from ``loadables``.
        """
        yield from self.run(loadables, Detect.CORRECTION, max_angle=max_angle, min_distance=min_distance)

    def timewarp_check(self, loadables) -> Iterable[TimewarpResult]:
        """
        Investigates loadables for aim correction.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to investigate.

        Yields
        ------
        :class:`~.CorrectionResult`
            A result representing an aim correction investigation into a
            loadable from ``loadables``.
        """
        yield from self.run(loadables, Detect.TIMEWARP)

    def load(self, loadable):
        """
        Loads a loadable.

        Parameters
        ----------
        loadable: :class:`~circleguard.loadable.Loadable`
            The loadable to load.

        Notes
        -----
        This is identical to calling ``loadable.load(cg.loader)``.
        """
        loadable.load(self.loader, self.cache)

    def load_info(self, loadable_container):
        """
        Loads a loadable container.

        Parameters
        ----------
        loadable: :class:`~circleguard.loadable.LoadableContainer`
            The loadable container to load.

        Notes
        -----
        This is identical to calling
        ``loadable_container.load_info(cg.loader)``.
        """
        loadable_container.load_info(self.loader)


    def set_options(self, cache=None):
        """
        Sets options for this instance of circlecore.

        Parameters
        ----------
        cache: bool
            Whether to cache loaded loadables.
        """

        # remnant code from when we had many options available in set_options.
        # Left in for easy future expansion
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

    Parameters
    ---------
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
