from pathlib import Path
import logging
from tempfile import TemporaryDirectory
from typing import Iterable, Union

from slider import Library

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator
from circleguard.cacher import Cacher
from circleguard.loadable import Check
from circleguard.enums import Detect
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
        instantiated with two args - a key and a cacher.
    """
    DEFAULT_ANGLE = 10
    DEFAULT_DISTANCE = 8
    # a healthy balance between speed and accuracy.
    DEFAULT_CHUNKS = 5

    def __init__(self, key, db_path=None, slider_dir=None, loader=None, \
        cache=True):
        self.cache = cache
        self.cacher = None
        if db_path is not None:
            # resolve relative paths
            db_path = Path(db_path).absolute()
            # they can set cache to False later with
            # :func:`~.circleguard.set_options` if they want; assume caching is
            # desired if db path is passed
            self.cacher = Cacher(self.cache, db_path)

        self.log = logging.getLogger(__name__)

        # allow for people to pass their own loader implementation/subclass
        LoaderClass = Loader if loader is None else loader
        self.loader = LoaderClass(key, self.cacher)

        if slider_dir is None:
            # have to keep a reference to it or the folder gets deleted and
            # can't be walked by Library
            self.slider_dir = TemporaryDirectory()
            self.library = None
        else:
            self.library = Library(slider_dir)


    def run(self, loadables, detect, loadables2=None, max_angle=DEFAULT_ANGLE, \
        min_distance=DEFAULT_DISTANCE, num_chunks=DEFAULT_CHUNKS) \
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
        num_chunks: int
            For :data:`detect.STEAL_CORR`, how many chunks to split the replay
            into when comparing. Note that runtime increases linearly with the
            number of chunks.

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
            comparer = Comparer(replays1, replays2, detect, num_chunks)
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
                    bm = library.lookup_by_id(replay.map_id, download=True, \
                                              save=True)
                investigator = Investigator(replay, detect, max_angle, \
                                            min_distance, beatmap=bm)
                yield from investigator.investigate()

            if detect & Detect.RELAX:
                if not self.library:
                    # disconnect from temporary library
                    library.close()


    def similarity(self, loadables, loadables2=None, method=Detect.STEAL_SIM, \
        num_chunks=DEFAULT_CHUNKS, single=False) \
        -> Union[Iterable[StealResult], StealResult]:
        """
        Calculates the similarity between each pair of replays in ``loadables``,
        of between each pair of replays with one from ``loadables`` and the
        other from ``loadables2``.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`]
            The loadables to calculate the similarity of.
        loadables2: list[:class:`~.Loadable`]
            If passed, compare each loadable in ``loadables``
            against each loadable in ``loadables2`` for replay stealing,
            instead of to other loadables in ``loadables``.
        method: :class`~.Detect`
            What method to use to investigate the loadables for replay stealing.
            This should be one of ``Detect.STEAL_SIM`` or ``Detect.STEAL_CORR``,
            or both (or'd together).
        num_chunks: int
            How many chunks to split the replay into when comparing. This
            parameter only has an affect if ``method`` is ``Detect.STEAL_CORR``.
            Note that runtime increases linearly with the number of chunks.
        single: bool
            If true, the investigation for snaps is evaluated immediately (as
            opposed to deferring execution with a generator, the default) and
            the first ``StealResult`` is returned.

        Yields
        ------
        :class:`~.StealResult`
            A result containing the similarity of a pair of replays from
            ``loadables`` and/or ``loadables2``. This function only yields (as
            opposed to returning) if ``single`` is ``False``.

        Returns
        -------
        :class:`~.StealResult`
            A result containing the similarity of a pair of replays
            ``loadables`` and/or ``loadables2``. This function only returns (as
            opposed to yielding) if ``single`` is ``True``.
        """
        result = self.run(loadables, method, num_chunks=num_chunks)
        if single:
            return list(result)[0]
        return result


    def ur(self, loadables, single=False) \
        -> Union[Iterable[RelaxResult], RelaxResult]:
        """
        Calculates the ur of each replay in ``loadables``.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`] or :class:`~.Loadable`
            The loadables to calculate the ur of. For convenience, passing a
            single loadable is equivalent to passing a list containing only that
            loadable.
        single: bool
            If true, the investigation for snaps is evaluated immediately (as
            opposed to deferring execution with a generator, the default) and
            the first ``RelaxResult`` is returned.

        Yields
        ------
        :class:`~.RelaxResult`
            A result containing the ur of the replay. This function only yields
            (as opposed to returning) if ``single`` is ``False``.

        Returns
        -------
        :class:`~.RelaxResult`
            A result containing the ur of the replay. This function only returns
            (as opposed to yielding) if ``single`` is ``True``.
        """
        result = self.run(loadables, Detect.RELAX)
        if single:
            return list(result)[0]
        return result


    def snaps(self, loadables, single=False) \
        -> Union[Iterable[CorrectionResult], CorrectionResult]:
        """
        Finds any snaps (sudden, suspicious movement) in each replay in
        ``loadables``.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`] or :class:`~.Loadable`
            The loadables to find snaps in. Passing a single loadable is
            equivalent to passing a list containing only that loadable; this is
            provided for convenience.
        single: bool
            If true, the investigation for snaps is evaluated immediately (as
            opposed to deferring execution with a generator, the default) and
            the first ``CorrectionResult`` is returned.

        Yields
        ------
        :class:`~.CorrectionResult`
            A result containing the snaps of the replay. This function only
            yields (as opposed to returning) if ``loadables`` contains more than
            1 replay.

        Returns
        -------
        :class:`~.CorrectionResult`
            A result containing the snaps of the replay. This function only
            returns (as opposed to yielding) if ``loadables`` contains exactly 1
            replay.
        """
        result = self.run(loadables, Detect.CORRECTION)
        if single:
            return list(result)[0]
        return result

    def frametime(self, loadables, single=False) \
        -> Union[Iterable[TimewarpResult], TimewarpResult]:
        """
        Calculates the average frametime and other frametime information for
        each replay in ``loadables``.

        Parameters
        ----------
        loadables: list[:class:`~.Loadable`] or :class:`~.Loadable`
            The loadables to calculate the frametime of. Passing a single
            loadable is equivalent to passing a list containing only that
            loadable; this is provided for convenience.
        single: bool
            If true, the investigation for snaps is evaluated immediately (as
            opposed to deferring execution with a generator, the default) and
            the first ``TimewarpResult`` is returned.

        Yields
        ------
        :class:`~.TimewarpResult`
            A result containing the frametimes of the replay. This function only
            yields (as opposed to returning) if ``single`` is ``False``.

        Returns
        -------
        :class:`~.TimewarpResult`
            A result containing the frametimes of the replay. This function only
            returns (as opposed to yielding) if ``single`` is ``True``.
        """
        result = self.run(loadables, Detect.TIMEWARP)
        if single:
            return list(result)[0]
        return result

    # TODO remove in core 5.0.0
    # @deprecated
    steal_check = similarity
    relax_check = ur
    correction_check = snaps
    timewarp_check = frametime


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
