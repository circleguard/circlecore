# Circlecore

Circlecore is the backend of the circleguard project, available as a pip module. If you are looking to download and start using circleguard yourself, see [our frontend repo](https://github.com/circleguard/circleguard). If you would like to incorporate circleguard into your own projects, read on.

To clarify, this module is referred to internally as circlecore to differentiate it from the circleguard project as a whole, but is imported as circleguard, and referred to as circleguard in this overview.

## Usage

First, install circleguard:

```bash
$ pip install circleguard
```

Circleguard can be ran in two ways - through convenience methods such as `circleguard.user_check()` or by instantiating and passing a Check object to `circleguard.run(check)`, which provides much more control over how and what replays to compare. Both methods return a generator containing Result objects.

The following examples provide very simple uses of Result objects. For more detailed documentation of what variables are available to you through Result objects, refer to its documentation in the source.

### Convenience Methods

For simple usage, you may only ever need to use convenience methods. These methods are used directly by the frontend of circleguard and are generally maintained on that basis, so methods useful to the most people are added. Convenience methods are no different from running circleguard through Check objects - internally, all convenience methods do is create Check objects and run circleguard with them anyway. They simply provide easy usage for common use cases of circleguard, such as checking a specific map's leaderboard.


```python
from circleguard import *

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")

# screen a user's top plays for replay steals and remods.
# You can change options such as whether to cache the results from the default for a single method. See Advanced Usage for more on default options.
for r in circleguard.user_check(12092800, cache=True):
    if(r.ischeat):
        print("Found a cheater! {} vs {}, {} set later.".format(r.replay1.username, r.replay2.username, r.later_name))

# cmopare the top 10 plays on a map for replay steals
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

The much more flexible way to use circleguard is to make your own Check object and run circleguard with that. This allows for mixing different types of Replay objects - comparing local .osr's to online replays - as well as the liberty to instantiate the Replay objects yourself and use your own Replay subclasses. See Advanced Usage for more on subclassing.

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

**Note that this section specifically is not accurate and only serves as notes for future implementation**

There are four tiers of options. The lowest option which is set takes priority for any given replay or comparison. Setting options does not effect previously instantiated objects - changing global options will only affect Circleguard objects created after the option is changed, for instance.

Options can be set at the highest level (global level) by using Circleguard.set_options. Options can be changed at the second highest level (instance level) using circleguard#set_options, which only affects the instance you call the method on. Be careful to use the static method to change global settings and the instance method to change instance settings.

Options can be further specified at the second lowest level (Check level) by passing the appropriate argument when the Check is instantiated. Finally, options can be changed at the lowest level (Replay level) by passing the appropriate argument when the Replay is instantiated.

### Subclassing Replay

If you have needs that are not met by the provided implementations of Replay - ReplayPath and ReplayMap - you can subclass Replay, or one of its subclasses, yourself.

Here is a simple example of subclassing, where each Replay has a unique id. Say you were pulling these paths from a database rather than listing the files in a folder - if your database has an id for each entry, storing that in the Replay allows you to identify which entry to modify in the database after a comparison has been made.

```python
from circleguard import *

class IdentifiableReplay(ReplayPath):
    def __init__(self, id, path):
        self.id = id
        ReplayPath.__init__(self, path)

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")
# database file here unrelated to the path database TODO rewrite example to make clearer or remove db path as necessary altogether
check = Check(IdentifiableReplay(1, "/path/to/osr.osr"), IdentifiableReplay(2, "/path/to/osr2.osr"))
for result in circleguard.run(check):
    print("id {} vs {} - cheating? {}".format(result.replay1.id, result.replay2.id, result.ischeat))
    # do some database logic with these two ids if applicable
```

Although Replay does not have the id attribute by default, because we subclassed ReplayPath and gave IdenitiableReplay the id attribute, the replays stored in the Result object will be that same IdentifiableReplay we passed to the Check constructor, and will have the id attribute.

**The Replays stored in replay1 and replay2 of the Result object are the same replays used to instantiate Check.**

Besides adding information to the Replay through the constructor, you can also control when and how it gets loaded by overloading its `load` method.

```python
from circleguard import *

class ReplayDatabase(Replay):
    def __init__(self, map_id, user_id, mods, detect=Detect.ALL):
        self.map_id = map_id
        self.user_id = user_id
        self.mods = mods
        self.detect = detect
        self.loaded = False

    def load(self):
        # execute (unimplented) sql to retrieve replay data from a local database. Assume the call returns a tuple (replay_id, replay_data)
        result = load_replay_from_database(self.map_id, self.user_id, self.mods)
        replay_id = result[0]
        replay_data = result[1]

        Replay.__init__(self.user_id, self.mods, replay_id, replay_data, self.detect, loaded=True)

replays = [ReplayDatabase(1699366, 12092800, 4), ReplayDatabase(1005542, 7477458, 16)]
for replay in replays:
    print("loading replay from local database")
    replay.load()

for result in circleguard.run(Check(replys)):
    print(result.similarity)
```

Circleguard only cares that Replay is initialized in a subclass's load method (technically, it only cares that the class has certain attributes, but that's nitpicking). When you call circleguard.run(check), the first thing it checks if check.loaded is True. If it is, it doesn't load any replays inside it. If not, it calls the load method on each replay in the check object that has replay.loaded set to False, skipping those that have replay.loaded set to True.

So long as your overriding load method loads valid replay_data and initializes the superclass Replay with appropriate values, you can either load it outside the circleguard.run(check) call, or leave the loading up to that call. Either way, the load method will be executed unless you set replay.loaded to True, which happens when you initialize Replay.

If you just want to add attributes but are happy with how the replays are loaded, subclass one of ReplayPath or ReplayMap. If you want to entirely change how the replay is loaded, subclass Replay.
