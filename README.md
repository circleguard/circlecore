# Circlecore

Circlecore is the backend of the circleguard project, available as a pip module. If you are looking to download and start using the program circleguard yourself, see [our frontend repository](https://github.com/circleguard/circleguard). If you would like to incorporate circleguard into your own projects, read on.

To clarify, this module is referred to internally as circlecore to differentiate it from the circleguard project as a whole, but is imported as circleguard, and referred to as circleguard in this overview.

## Usage

First, install circleguard:

```bash
pip install circleguard
```

Circleguard can be run in two ways - through convenience methods such as `circleguard.user_check()` or by instantiating and passing a Check object to `circleguard.run(check)`, the latter of which provides much more control over how and what replays to compare. Both methods return a generator containing Result objects.

The following examples provide very simple uses of Result objects. For more detailed documentation of what variables are available to you through Result objects, refer to its documentation in the code.

### Convenience Methods

For simple usage, you may only ever need to use convenience methods. These methods are used directly by the frontend of circleguard and are generally maintained on that basis, so methods useful in the most number of situations are used. Convenience methods are no different from running circleguard through Check objects - internally, all convenience methods do is create Check objects and run circleguard with them anyway. They simply provide easy usage for common use cases of circleguard, such as checking a specific map's leaderboard.

```python
from circleguard import *

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")

# screen a user's top plays for replay steals and remods.
# You can change options such as whether to cache the results from the default for a single method. See Advanced Usage for more on default options.
for r in circleguard.user_check(12092800, cache=True):
    if(r.ischeat):
        print("Found a cheater! {} vs {}, {} set later.".format(r.replay1.username, r.replay2.username, r.later_name))

# compare the top 10 plays on a map for replay steals
for r in circleguard.map_check(1005542, num=10):
    if(r.ischeat):
        print("Found a cheater on a map! {} vs {}, {} set later.".format(r.replay1.username, r.replay2.username, r.later_name))

# compare local files for replay steals
for r in circleguard.local_check("/absolute/path/to/folder/containing/osr/files/"):
     if(r.ischeat):
        print("Found a cheater locally! {} vs {}, {} set later.".format(r.replay1.path, r.replay2.path, r.later_name))

# compare two specific users' plays on a map to check for a replay steal
for r in circleguard.verify(1699366, 12092800, 7477458, False):
    if(r.ischeat):
        print("Confirmed that {} is cheating".format(r.later_name))
    else:
        print("Neither of those two users appear to have stolen from each other")
```

### More Generally

The much more flexible way to use circleguard is to make your own Check object and run circleguard with that. This allows for mixing different types of Replay objects - comparing local .osr's to online replays - as well as the liberty to instantiate the Replay objects yourself and use your own Replay subclasses. See [Advanced Usage](#subclassing-replay) for more on subclassing.

```python
from circleguard import *
from pathlib import Path

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")

# assuming you have your replays folder in ../replays, relative to your script. Adjust as necessary
PATH = Path(__file__).parent / "replays"
# assuming you have two files called woey.osr and ryuk.osr in the replays folder.
# This example uses python Paths, but strings representing the absolute file location will work just fine.
# Refer to the Pathlib documentation for reference on what constitutes a valid Path in string form.
replays = [ReplayPath(PATH / "woey.osr"), ReplayPath(PATH / "ryuk.osr")]
check = Check(replays)
for r in circleguard.run(check):
    if(r.ischeat):
        print("Found a cheater locally! {} vs {}, {} set later.".format(r.replay1.path, r.replay2.path, r.later_name))

# Check objects allow mixing of Replay subclasses. circleguard only defines ReplayPath and ReplayMap,
# but as we will see further on, you can define your own subclasses to suit your needs.
replays = [ReplayPath(PATH / "woey.osr"), ReplayMap(map_id=1699366, user_id=12092800, mods=0)]
for r in circleguard.run(Check(replays)):
    if(r.ischeat):
        # subclasses are mixed now
        repr1 = r.replay1.path if r.replay1 is ReplayPath else r.replay1.username
        repr2 = r.replay2.path if r.replay2 is ReplayPath else r.replay2.username
        print("Found a cheater! {} vs {}, {} set later.".format(repr1, repr2, r.later_name))
```

## Advanced Usage

### Setting Options

There are four tiers of options. The lowest option which is set takes priority for any given replay or comparison.

Options can be set at the highest level (global level) by using `Circleguard.set_options`. Options can be changed at the second highest level (instance level) using `circleguard#set_options`, which only affects the instance you call the method on. Be careful to use the static module method to change global settings and the instance method to change instance settings, as they share the same name and can be easy to confuse.

Options can be further specified at the second lowest level (Check level) by passing the appropriate argument when the Check is instantiated. Finally, options can be changed at the lowest level (Replay level) by passing the appropriate argument when the Replay is instantiated.

Settings affect all previously instantiated objects when they are changed. That is, if you change an option globally, it will change that setting for all past and future Circleguard instances.

### Subclassing Replay

If you have needs that are not met by the provided implementations of Replay - `ReplayPath` and `ReplayMap` - you can subclass Replay (or one of its subclasses) yourself.

The following is a simple example of subclassing, where each Replay is given a unique id. If, for example, you want to distinguish between loading an otherwise identical replay at 12:05 and 12:07, giving each instance a unique id would help in differentiating them. This is a somewhat contrived example (comparing a replay against itself will always return a positive cheating result), but anytime you need to add extra attributes or methods to the classes for any reason, it's simple to subclass them.

```python
from circleguard import *

class IdentifiableReplay(ReplayPath):
    def __init__(self, id, path):
        self.id = id
        super().__init__(path)

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")
check = Check(IdentifiableReplay(1, "/path/to/same/osr.osr"), IdentifiableReplay(2, "/path/to/same/osr.osr"))
for result in circleguard.run(check):
    print("id {} vs {} - cheating? {}".format(result.replay1.id, result.replay2.id, result.ischeat))
```

Although Replay does not have the id attribute by default, because we gave our `Check` object `IdentifiableReplays`, it will spit back `IdentifiableReplays` back at us when we run the check, and we can access our id attribute.

Besides adding information to the Replay through the constructor, you can also control when and how it gets loaded by overloading its `load` method. The following example is again contrived, because we provide a database implementation for you (any replays you attempt to load through the api will be loaded from the database instead, if you had previously downloaded and cached them), but hopefully gets the point of overloading `load` across.

```python
from circleguard import *

class ReplayDatabase(Replay):
    def __init__(self, map_id, user_id, mods, detect=Detect.ALL):
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect
        self.loaded = False

    def load(self, loader, cache=None):
        # execute some sql (implementation not shown) to retrieve replay data from a local database. Assume the call returns a tuple of (replay_id, replay_data)
        result = load_replay_from_database(self.map_id, self.user_id, self.mods)
        replay_id = result[0]
        replay_data = result[1]

        Replay.__init__(self, self.user_id, self.mods, replay_id, replay_data, self.detect, loaded=True)

replays = [ReplayDatabase(1699366, 12092800, 4), ReplayDatabase(1005542, 7477458, 16)]
for replay in replays:
    print("loading replay from local database")
    replay.load()

for result in circleguard.run(Check(replys)):
    print(result.similarity)
```

To get around the rather hairy problem of simultaneously allowing users to instantiate Replay subclasses at any point in their program and only loading them when necessary (when calling `circleguard#run(check)`), circleguard opts to wait to initialize the Replay superclass until the load method is called and we have all the necessary information that the Replay class requires, either from the api, a local osr file, or some other means.

This means that if you subclass Replay, you must make sure you do a couple of things that circleguard expects from any Replay subclass. Replay must be initialized in your `load` method (**NOT** in your `__init__` method, as you would expect), and you must set self.weight to one of `RatelimitWeight.HEAVY`, `RatelimitWeight.LIGHT`, or `RatelimitWeight.NONE` in your `__init__` method (**NOT** in your load method! Circleguard needs to know how much of a toll loading this replay will cause on the program before it is loaded). The documentation from the Ratelimit Enum follows, for your convenience:

```python
"""
How much it 'costs' to load a replay from the api. If the load method of a replay makes no api calls,
the corresponding value is RatelimitWeight.NONE. If it makes only light api calls (anything but get_replay),
the corresponding value is RatelimitWeight.LIGHT. If it makes any heavy api calls (get_replay), the
corresponding value is RatelimitWeight.HEAVY.

This value is used internally to determine how long the loader class will have to spend loading replays -
currently LIGHT and NONE are treated the same, and only HEAVY values are counted towards replays to load.
See loader#new_session and the Replay documentation for more details.
"""
```

`replay_data` must be a list of `circleparse.ReplayEvent` like objects when passed to `Replay.__init__`. You can look at the [circleparse](https://github.com/circleguard/circleparse) repository for more information, but all that means is that each object must have the `time_since_previous_action`, `x`, `y`, and `keys_pressed` attributes.

Finally, the load method of the replay must accept one required argument and one positional argument, regardless of whether you use them - `loader` and `cache=None`, respectively. If you need to load some information from the api, use the passed Loader class to do so (see the Loader class for further documentation). Should you want to implement a caching system of your own, the cache argument takes care of all the nasty options hierarchy issues and delivers you the final result - should this singular replay be cached? If you choose to cache the replay, you will also have to implement the loading of the replay from the cache, by writing the corresponding logic in the load method. None of that is touched by circleguard - the caching of ReplayMaps happens in an entirely different location than `replay#load`. So long as you set `self.loaded` to `True` by initializing Replay in `load`, circleguard will respect your replay and assume you have loaded the data properly.

### Loading Replays

Normally, all replays in a `Check` object are loaded when you call `circleguard#run(check)`. However, if you require more control over when you load your replays (or which ones get loaded when you do), you can call `circleguard.load(replay)` to load an individual replay. This is a shorthand method for calling `replay#load(circleguard.loader)`, and going through circleguard is always recommended, as not doing so can cause unexpected caching issues with the settings hierarchy not cascading down to the replay correctly. See the last section of Subclassing Replay for more on the optional cache option for `replay#load`.

There is no limitation on the order in which replays get loaded; when `circleguard#run(check)` is called, it first checks if `check.loaded` is `True`. If it is, it assumes all the replays in the check object are loaded as well and moves on to comparing them. Else, it checks if each replay in the check object have `replay.loaded` set to `True` - if so, it moves on to loading the next replay. Otherwise, it calls `replay#load`.

## Contributing

If you would like to contribute to Circleguard, join our discord and ask what you can help with, or take a look at the [open issues for circleguard](https://github.com/circleguard/circleguard/issues) and [circlecore](https://github.com/circleguard/circlecore/issues). We're happy to work with you if you have any questions!

You can also help out by opening issues for bugs or feature requests, which helps us and others keep track of what needs to be done next.

## Conclusion

Whether you read through everything or scrolled down to the bottom, I hope this helped. If you have any questions, the link to our discord follows. We welcome any comments and are happy to answer questions.

Discord: <https://discord.gg/VNnkTjm>
