# v5.1.3

* add convenience `cg.ReplayMap`, `cg.ReplayPath`, `cg.ReplayString`, and `cg.ReplayID` methods which create loaded loadables
* loading a nonexistent replay will now raise `NoInfoAvailable` like it used to (this had regressed recently)
* raise `ValueError` on replays with empty replay data

# v5.1.2

* add `fuzzy_mods` utils method, which allows you to pass a required mod and a list of optional mods, and a list of each possible mod combination is returned
* require snaps to also be in the hitwindow of a hitobj to be counted when using `only_on_hitobjs=True`
  * Previously, snaps could be counted when they were "on" the closest hitobj, even though that hitobj might be many seconds in the past or future
* move to [osrparse](https://github.com/kszlim/osu-replay-parser) for osr parsing instead of [circleparse](https://github.com/circleguard/circleparse)

# v5.1.1

* require `slider>=0.4.0` instead of `slider~=0.4.0`

# v5.1.0

* add `only_on_hitobjs` parameter to `cg.snaps` (defaults to `True`) which, if set, only returns snaps that occur on hitobjects
* all hitobjects returned by `Circleguard` methods (from `cg.snaps` and `cg.hits`, for instance) are now converted to their hard_rock form if the replay had HR enabled
* add convenience method `cg.beatmap(replay)` which returns the beatmap associated with the given replay
* expose hitobject classes in `__init__.py`

# v5.0.3

* fix maps with no replays for a mod combo throwing `NoInfoAvailableException`
* required `slider ~= 0.3.1` instead of `slider == 0.3.1`

# v5.0.2

* remove `Mod.__ne__` as it's the inverse of `Mod.__eq__` by default if ne doesn't exist

# v5.0.1

* return ndarray instead of list in `Circleguard#frametimes`
* add `Circleguard#frametime_graph` to generate a frametime graph from a replay. This requires that you have `matplotlib` installed
* add `__str__` and `__repr__` to `Hit`
* fix ur and hits erroring on maps that have catmull sliders

# v5.0.0

* `steal_check`, `relax_check`, `correction_check`, `timewarp_check` have been removed as deprecated, and `run` has been removed. Use `similarity`, `ur`, `snaps`, `frametime`, or a combination thereof instead
* the `single` parameter has been removed from `similarity`, `ur`, `snaps`, `frametime`. These functions now only accept a replay (or pair of replays, in `similarity`'s case) instead of a `LoadableContainer`. Instead of passing a `LoadableConatainer` to these functions, you should iterate over the container and call the function with single replays
* new `cv` parameter for `ur`, `frametime`, `frametimes`, which allows you to choose if you want the return value to be converted or unconverted
* new `within` parameter for `hits`, which returns only hits within a certain distance from the edge of the hitobject
* new functions `cg.Map`, `cg.User`, `cg.MapUser` which create the corresponding `ReplayContainer` and loads its info. This is shorthand for writing (for example):

```python
u = User(...)
cg.load_info(u)
```

* new `mods_unknown` parameter to `similarity`, `frametime`, `frametimes`, which allows replays with unknown mods to still be processed, with the behavior specified by `mods_unknown`. This is useful e.g. for finding the similarity of two `ReplayID`s, as `ReplayIDs` do not provide mods due to api limitations
* `Detect` has been removed entirely. If you were using `Detect.SIM_LIMIT` or `Detect.CORR_LIMIT`, see `Circleguard.SIM_LIMIT` and `Circleguard.CORR_LIMIT` as a replacement. Any other members have been permanently removed
* `Result` and all subclasses have been removed. `Circleguard` methods now return the important result (such as a number or list) directly instead of wrapping it behind a `Result`
* `ResultType` has been removed
* circleguard-specific exceptions have been replaced by base python exceptions where possible
* the `version` attribute of `Replay`s has been renamed to `game_version` and is now a new class, `GameVersion`, which subclasses int and provides additional functionality
* `x` and `y` attributes have been added to `Hit`
* the `hitobject` attribute of `Hit` is now a circleguard `Hitobject` object instead of a slider `Hitobject` object
* new `Hit#distance` function which calculates the distance of the hit to either the edge or center of the hitobject
* new `Hit#within` function which returns true if the hit was within a certain distance of the edge of the hitobject
* for all intents and purposes, `LoadableContainer` has been removed. It is still available under the same name, but nothing inherits from it any more and it provides different functionality (acting as a true container and providing convenience operations on a list of `Loadable`s)
* `Check` has been removed
* `Replay`s have a new `map_info` attribute, which provides information about where their map can be found, either online or locally
* new `Replay#beatmap` method, which loads the beatmap tied to the replay. This allows replay subclasses to have complete control over how they load their beatmap and which beatmap gets loaded
* new `Replay#has_data()` method, which should be preferred instead of checking `replay.replay_data is not None`
* `ReplayMap` and `ReplayPath` equality now checks replay data explicitly if both replays being compared are loaded
* new `order` utils method which takes two replays and returns a 2-tuple where the earlier replay is first and the later replay is second. This is intended to be used to replace `steal_result.earlier_replay` and `steal_result.later_replay`. Example usage:

```python
(earlier_replay, later_replay) = order(r1, r2)
```

* new `replay_pairs` method which takes two lists of replays and returns a list of pairs of replays that should be compared against each other to cover all cases of replay stealing in the two lists. This is intended to be used in place of passing a `ReplayContainer` to `cg.similarity`, which no longer accepts iterables. Example usage:

```python
m = cg.Map(221777, span="1-2")
for (replay1, replay2) in replay_pairs(m):
    print(cg.similarity(replay1, replay2))
```

* KeylessCircleguard now has better error messages if you misuse it
* tutorial has been rewritten

# v4.5.1

* implement `__hash__` for Replay subclasses

# v4.5.0

* add `KeylessCircleguard` class, which does not require a key to be instantiated and can do everything `Circleguard` can, with the requirement that the passed loadables are already loaded
* add `Circleguard#hits` method, which returns a list of the hits in the replay (where the user hit a hitobject)
* add `keydowns` attribute to `Replay` classes, which is a list of the keys pressed for each frame that were not pressed in the previous frame
* implement `__hash__` for `Snap`

# v4.4.1

* add new `ReplayString` class, which allows instantiation from a byte string that contains the contents of an osr file (#159)
* rename `ReplayPath.hash` to `ReplayPath.beatmap_hash`

# v4.4.0

* improve ur calculation, which should now usually be exactly correct and sometimes slightly (1-3 ur) off
* rename `*_Check` methods to better describe their use as a statistic calculation
* add a `single` argument to `*_Check` methods which will immediately evaluate the investigation and return the first result if `True`
* add user id, map id, and mods index to newly created caches

# v4.3.4

* pin scipy to 1.4.1 (pyinstaller does not yet have a hook for scipy 1.5.0, which just came out yesterday)

# v4.3.3

* expose full frametime list in `TimewarpResult`

# v4.3.2

* fix `Mod` instances not being comparable to `ModCombination` instances (eg `Mod("DT") == Mod.DT` was `False` and is now `True`)
* fix mod initialization from strings not adding `DT` (or `SD`) when parsing `NC` (`PF`)
* add `Mod` / `ModCombination` tests

# v4.3.1

* fix `TimewarpResult` being missing from `__all__`

# v4.3.0

* add basic timewarp detection (just calculates the median of the frametimes)

# v4.2.2

* fix ``ReplayCache`` and ``ReplayDir`` double counting replays sometimes (for real this time)

# v4.2.1

* fix ``ReplayCache`` and ``ReplayDir`` double counting replays sometimes

# v4.2.0

* add several new ``Loadable`` convenience classes. ``ReplayCache`` for accessing random elements from a circlecore database, ``ReplayDir`` for folders of ``.osr`` files, and ``ReplayID`` for when you only know the replay id.

# v4.1.2

* correctly account for skips in replays

# v4.1.1

* don't reorder frames with the same time

# v4.1.0

* add a new replay stealing detect, `Detect.STEAL_CORR`, using signal processing cross-correlation methods
* rename `Detect.STEAL` to `Detect.STEAL_SIM`, with `Detect.STEAL` remaining as deprecated
* split `StealResult` into `StealResultSim` and `StealResultCorr`
* correctly order replay frames and remove invalid frames. This changes similarity values slightly
* add default cutoffs to `Detect` as `SIM_LIMIT` and `UR_LIMIT`. These are values we feel are enough to call a replay cheated. They are not used in our code but are provided as a convenience.
* don't remove frames with identical time values when processing replay data. This removal still occurrs, but only when the replays are investigated.

# v4.0.2

* loading replays from cache is now roughly twice as fast

# v4.0.1

* fix `ReplayMap`s inside a `Map` not having some attributes set after the `Map` is info loaded

# v4.0.0

* add `cg.steal_check`, `cg.relax_check`, and `cg.correction_check` as convenience methods. These methods call `cg.run` internally
* don't require `Check` when using `cg.run`. `cg.run` now accepts an iterable of `Loadable`s and a `Detect`
* provide cvUR as `result.ur` and ucvUR as `result.ucv_ur`
* add new `Span` class, which can be used to represent a range of numbers with a string
* remove `num` argument to loadables. Use the `Span` class, or an appropriate string, instead
* remove `ischeat` from `Result`s and remove thresholds for determining a cheated replay. Users should determine their own threholds and check against `Result` attributes
* make `Detect` an `IntFlag` instead of a full class
* add default `load` and `load_info` implementations to `LoadableContainer`
* don't use `Replay.__init__` to process replay data. Use `Replay#_process_replay_data` instead
* require `cache` in `Loadable` instantiation
* add `Loader.MAX_MAP_SPAN` and `Loader.MAX_USER_SPAN`, representing the most replays you can get from a map and user respectively

# v3.2.3

* fix error while investigating replays with no replay data

# v3.2.2

* fix error when loading a replay that has replay info but is not downloadable
* InfoLoadable renamed to LoadableContainer
* cache passed as part of super call
* `__eq__` required for Loadable
* `num_replays` method removed (should use `len(loadable_container.all_replays()` instead)
* all_replays required by `LoadableContainer`, not `Loadable`
* default implementation of `__iter__` and `__getitem__` in LoadableContainer
* `check.all_replays()` now returns the expected value (`loadables1 + loadables2`), new method `#all_replays1` which returns only the replays in `loadables1`.

## Now using ossapi v1.2.3

* use 15 second timeout for requests

# v3.2.1

* correctly calculate ur for replays using mouse clicks (as opposed to keyboard clicks).

# v3.2.0

* rename `ReplayStealingResult` to `StealResult` (for consistency with `Result` names matching their respective `Detect` names). `ReplayStealingResult` left available as deprecated.
* mods can now be instantiated through `Mod`. Instantiation through `ModCombination` is highly discouraged.
* mods can now be instantiated with a string, as well as an int. The string must be a combination, in any order, of the two length strings that represent mods. For instance, `Mod("HDHR")` is valid, and `Mod("HDHR") == Mod.HDHR` is `True`.
* use `np.interp` instead of a homebrew interpolation.
  * changes similarity values slightly, both increasing and decreasing simvals for legit and stolen replays.
  * no measurable impact on the effectiveness of circlecore to detect stolen replays.
  * increases comparison speed.
* use only unique timestamps when interpolating (also changes similarity values slightly)

# v3.1.0

* fix `MapUser` inheritence (now properly inherits from `ReplayContainer`)
* fix incorrect `__add__` method for `Check`
* rename `Keys` to `Key` (`Keys` left available as deprecated)
* don't double load `ReplayInfo` when using `Map`
* fix mod subtraction not being commutative (eg `Mod.HDHR - Mod.HR` has a different meaning from `Mod.HR - Mod.HDHR`)
* store beatmap hash in `ReplayPath`
* properly check response for `map_id`, `user_id`, and `username` functions
* enforce ratelimit to all Loader functions
* don't reraise `InvalidKeyException` as a `CircleguardException`
* add CHANGELOG file to both track unreleased changes and past changes
* various documentation links and wording fixes

# v3.0.0

## Important

* add aim correction detection
* new forward-facing documentation built with sphinx, including a comprehensive introduction on how to use circlecore (<https://docs.circleguard.dev/>)
* new `User` class which represents a user's top plays
* new `MapUser` class which represents all of a user's plays on a map
* new `Mod` and `ModCombination` class which represent mods
* restructure `replay.py` and inheritance of `loadables`. `Container` is (roughly) replaced with `InfoLoadable`, and `Check` is the only entry point for `Detect`.
* major `Detect` restructure; split into subclasses per cheat type. A `Detect` is instantiated with its respective thresholds(steal, ur, etc) instead of thresholds being global settings
* `Map` and `User` are now iterable and indexable, referencing `Replay`s in the `Map` or `User`
* rewrite and update all internal documentation
* `Circleguard` now takes a `cache` argument, which can make the database effectively read-only

## Not so Important

* switch documentation style from google to numpy (<https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard>)
* new method `cg.load_info` that loads the info for `ReplayContainer`s
* global settings almost entirely removed, save for `loglevel`
* instance settings almost entirely removed, save for `cache`
* rename `replay.py` to `loadable.py`
* rename `UserInfo` to `ReplayInfo`
* `Options` class removed
* add a `loader#username` function which retrieves a username from a user id. See also <https://github.com/ppy/osu-api/issues/281>
* add an `lru_cache` to `loader#map_id`, `#user_id`, and `#username` functions
* `loader#get_user_best` now returns a list of `UserInfo`, and accepts a `mods` argument.
* `cg.run` now only accepts a `Check`
* replace int mods with `ModCombination` in most places
* add ScoreV2 mod. Fixes not being able to process ScoreV2 replays.
* create a slider `Library` every time `#run` is called if `slider_dir` is not passed. Fixes `PermissionError`s on windows.
* remove convenience methods (`user_check`, `map_check`, etc). These have been replaced by `Map` and `User` (new)
* update STYLE document
* all Circleguard instances now use the same logger
* `filter` argument removed throughout the codebase
* `RatelimitWeight` and `ResultType` enum string values capitalized
* `ResultType.AIM_CORRECTION` renamed to `CORRECTION`
* `#ur` is now a staticmethod in `Investigator`

# v2.4.0

* new Map class for conveniently specifying a range of replays on a map that can be ran directly with cg.run()
* new span argument to loadables and map_check and user_check which specify exactly which of the top replays to check
* restructure of Replays and Checks. Both now inherit from Loadable, and Check and Map inherit from Container. Containers can hold other Containers, to an arbitrary depth. cg.run() now accepts any Container.
* use Slider to download beatmaps for relax detection
* fix user_check not using the same args as create_user_check
* check.filter() now requires a Loader
* add test cases for different replay types
* REPLAY_STEALING and REMODDING ResultType renamed to STEAL and REMOD respectively
* optimize ur calculation
* fix RelaxResult returning timestamped data in `result.replay` instead of the replay
* keys enum is now an IntFlag instead of an Enum
* update test cases for cookiezi's new name (chocomint)
* comparer decides mode on its own and does not need a mode in Comparer#compare
* clean up ColoredFormatter code

# v2.3.1

* fix error when running local check with both u and map id
* throw NoInfoAvailableException on empty api response

# v2.3.0

* cg.load now accepts either a Check object or a Replay object. Passing a check will result in all replays stored in the check being loaded.
* cg.load no longer requires a Check to load a replay.
* settings overhaul - settings now cascade properly and at different times than before.
* test suite added (not covering everything, yet)
* fix error when setting an Option class value (infinite recursion)

# v2.2.0

* add relax cheat detection (and consequently UR calculation)
* allow circleguard to be used without a database
* add mods argument to map_check
* add Detect settings to global/cg/check/replay
* retry requests if JSONDecodeError response is returned by ossapi
  * avoids fatal error while replay loading if api returns invalid response
* fix `pip install circleguard` failing if requirements were not installed
* minor readme example updates
* remove load progress tracking from Loader

## Now Using ossapi 1.2.2

* return custom response for JSONDecodeError when api returns invalid json

## Now using circleparse 6.1.0

* replay_id now parses to an int instead of a tuple
* add <https://github.com/osufx/osu-parser> files for more complicated parsing
* switch license to GPL3 to comply with osu-parser license

# v2.1.0

* fix convenience options not having effect when passing falsy values
* load map id and user id for local osrs
* fix fatal error when ratelimit is barely hit and proceeded by light api calls
* require map_id, user_id, and timestamp in Replay
* provide earlier_replay and later_replay in Result class that reference either replay1 or replay2 depending on timestamp order (and remove later_name) (#78)

# v2.0.2

* fix false positive when the user being checked was on the map leaderboard being checked with map check
* fix false positive with user screen when user was on leaderboard of their top plays
* fix error when trying to load only a single replay from a map

# v2.0.1

* differentiate loggers between circleguard instances
* add missing cache option to convenience methods
* add map and user options to create_local_check

# v2.0.0

This release splits `Circleguard` into `circlecore` (pip module) and `circleguard` (gui with `pyqt` as the frontend, using `circlecore` as the backend).

Changes:

* replays can be loaded from arbitrary locations (db, osu website, mirror website, osr file)
* convenience methods for common use cases added (checking a map or user)
* support for comparing two arbitrary replays (from two different maps, if you so choose)
* logging overhaul, any important action is logged
* major code cleanup
* removal of command line interface
* code standardized for pip upload (`setup.py`, `__init__.py`, etc)

# v1.3.3

* fix non-osr files being loaded as osr

# v1.3.2

* fix replay being compared against itself with -m -u

# v1.3.1

* fix fatal error when using both -l and -m flags

# v1.3.0

* new profile screener that checks a user's top n plays for replay stealing and remodding when -u flag only is passed
* ability to restrict what replays are downloaded (and compared) with the --mods flag
* major internal cleanup with the addition of the user_info class
* fix names starting with an underscore not being displayed on graphs

## Now using circleparse v4.0.1

* don't fatal error when rng seed is not present when we expect it to be
* fix wrong name to int mappings
* add scorev2 (fixes fatal error on attempting to parse a replay with the scorev2 mod)

## Now using ossapi v1.1.1

* filter out None values, not None keys, in kwargs parameters

# v1.2.0

* now detect steals which either have hr added or hr removed from the replay it was stolen from
* print progress every 10% when comparing replays
* print loading progress every time there is a pause for ratelimits while loading beatmaps
* move api wrapper to separate repo; formalize api calls
* catch and retry Request related exceptions
* potentially fix matplotlib printing "invalid command name" (#43)
* fix error when redownloading outdated replays

## Now using circleparse v3.2.1

* parse rng seed value from last frame of lzma (previously, nonsensical values such as -12345|0|0|10186099 were stored in the replay data)

## Now using ossapi v1.0.0

* move api wrapper to separate repo

# v1.1.0

* new --verify flag designed for staff use that checks if replays by two users on a given map are copies
* add --version flag that prints program version
* program renamed to circleguard (thanks to InvisibleSymbol for the name)
* print usernames instead of user ids for OnlineReplay comparisons
* use a single replay folder for local comparisons instead of two
* change default threshold to 18
* highlight the later replay instead of the first replay in printout
* remove --single flag (this is now default behavior when -l is set)
* load local replays per circleguard instance (fixes incosistent gui behavior)
* handle "Replay retrieval failed." api response
* fix None replays being compared after handling api error response
* force gui comparisons to not visualize replays (avoid multithreading crashes)
* raise properly sublclassed exceptions instead of base Exception
* only revalidate users that are actually stored in local cache
* properly compress replays that use smoke key (see v1.1.1 wtc-lzma-compression)

## Now using wtc-lzma-compression v1.1.1

* treat z stream as a signed byte instead of unsigned

# v1.0.0

* original release
