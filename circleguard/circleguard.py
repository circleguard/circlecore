from pathlib import Path
import logging
from tempfile import TemporaryDirectory
from typing import Iterable, Union

from slider import Library

from circleguard.loader import Loader
from circleguard.comparer import Comparer
from circleguard.investigator import Investigator, Hit, Snap
from circleguard.cacher import Cacher


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
            self.cacher = Cacher(self.cache, db_path)

        self.log = logging.getLogger(__name__)

        # allow for people to pass their own loader implementation/subclass.
        # Mostly exposed for circleguard (the gui).
        LoaderClass = Loader if loader is None else loader
        self.loader = LoaderClass(key, self.cacher)

        if slider_dir is None:
            # have to keep a reference to it or the folder gets deleted and
            # can't be walked by Library
            self.slider_dir = TemporaryDirectory()
            self.library = None
        else:
            self.library = Library(slider_dir)



    def similarity(self, replay1, replay2, method="similarity", \
        num_chunks=DEFAULT_CHUNKS, single=False) -> float:
        """
        Calculates the similarity between ``replay1`` and ``replay2``.

        Parameters
        ----------
        replay1: :class:`~circleguard.loadable.Replay`
            The replay to compare against ``replay2``.
        replay2: :class:`~circleguard.loadable.Replay`
            The replay to compare against ``replay1``.
        method: str
            What method to use to investigate the loadables for replay stealing.
            This must be one of ``similarity`` or ``correlation``.
        num_chunks: int
            How many chunks to split the replay into when comparing. This
            parameter only has an affect if ``method`` is ``correlation``.
            Note that runtime increases linearly with the number of chunks.

        Returns
        -------
        float
            If ``method`` is ``similarity``, this is the similarity of the two
            replays, which is (roughly speaking) the average distance between
            the two replays in pixels. A replay compared to itself (or an exact
            copy) has a similarity of 0.
            <br>
            If ``method`` is ``correlation``, this is the correlation between
            the two replays.
            # TODO explain correlation lol
        """
        pass



    def ur(self, replay, cv=True) -> float:
        """
        Calculates the unstable rate of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadable.Replay`
            The replay to calculate the ur of.
        cv: bool
            Whether to return the converted or unconverted ur. The converted ur
            is returned by default.

        Returns
        -------
        float
            The ur of the replay. This ur is converted if ``cv`` is ``True``,
            and unconverted otherwise.
        """
        ...


    def snaps(self, replay) -> Iterable[Snap]:
        """
        Finds any snaps (sudden, jerky movement) in ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadable.Replay`
            The replay to find snaps in.

        Returns
        -------
        list[Snap]
            The snaps of the replay. This list is empty if no snaps were found.
        """
        ...

    def frametime(self, replay) -> float:
        """
        Calculates the average frametime of ``replay``.

        Parameters
        ----------
        replay: :class:`~circleguard.loadable.Replay`
            The replay to calculate the average frametime of.

        Returns
        -------
        float
            The average frametime of the replay.
        """
        ...

    def hits(self, replay) -> Iterable[Hit]:
        self.load(replay)
        # fall back to temporary library if necessary
        library = self.library or Library(self.slider_dir.name)
        bm = library.lookup_by_id(replay.map_id, download=True, save=True)
        return Investigator.hits(replay, bm)


    def load(self, loadable):
        """
        Loads the ``loadable``.

        Parameters
        ----------
        loadable: :class:`~circleguard.loadable.Loadable`
            The loadable to load.

        Notes
        -----
        This is identical to calling ``loadable.load(cg.loader, cg.cache)``.
        """
        loadable.load(self.loader, self.cache)

    def load_info(self, loadable_container):
        """
        Loads the ``loadable_container``.

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


class KeylessCircleguard(Circleguard):
    """
    A :class:`~.Circleguard` for when you do not have access to an api key, but
    have loaded :class:`~circleguard.loadable.Loadable`\s that you want to
    perform operations on. It should go without saying that instances of this
    class cannot do anything that requires api access.

    Parameters
    ----------
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

    def __init__(self, db_path=None, slider_dir=None, loader=None, cache=True):
        # it's sufficient but not particularly rigorous to pass an invalid api
        # key here, and might interfere with future improvements (such as
        # checking the validity of the api key automatically on init).
        # TODO potentially improve this with an explicit `keyless` parameter
        # to `Circleguard` which allows for special `Loader` behavior
        super().__init__("INVALID_KEY", db_path, slider_dir, loader, cache)

    # TODO override most (all?) methods from `Circleguard` and either raise an
    # exception (if they always require api access, like `load` or `load_info`)
    # or first check that the loadables passed are all loaded, and raise an
    # exception otherwise.
    # This exception raising is purely to generate less confusing error
    # messages, as users would probably otherwise see an `ossapi` exception
    # complaining about an invalid key. Which is pretty clear, but we can do
    # better.


def set_options(*, loglevel=None):
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
