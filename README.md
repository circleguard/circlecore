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
import circleguard

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
import circleguard
from pathlib import Path

circleguard = Circleguard("your-api-key", "/absolute/path/to/your/db/file.db")

# assuming you have your replays folder in ../replays, relative to your script. Adjust as necessary
PATH = Path(__file__).parent / "replays"
# assuming you have two files called woey.osr and ryuk.osr in the replays folder.
# This example uses python Paths, but strings representing the absolute file location will work just fine.
# Refer to the Pathlib documentation for reference on what constitutes a valid Path in string form.
replays = [ReplayPath(PATH / "woey.osr"), ReplayPath(PATH / "ryuk.osr")]
check = Check(replays)
for result in circleguard.run(check):
    if(r.ischeat):
        print("Found a cheater locally! {} vs {}, {} set later.".format(r.replay1.path, r.replay2.path, r.later_name))

# Check objects allow mixing of Replay subclasses. circleguard only defines ReplayPath and ReplayMap,
# but as we will see further on, you can define your own subclasses to suit your needs.
replays = [ReplayPath(PATH / "woey.osr"), ReplayMap(map_id=1699366, user_id=12092800, mods=0)]
for result in circleguard.run(Check(replays)):
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

TODO
