# Circlecore

This is the core of the circleguard project, available as a pip module. To install, simply:

```bash
$ pip install circleguard
```

Example usage:

```python
from circleguard import *

circleguard = Circleguard() # exact constructor usage to be determined
for result in circleguard.run():
    if(result.is_cheater):
        print("Found a cheater! User id: {}, cheat type: {}:".format(result.user.id, result.cheat_type))
        if(type(result.cheat_type) is ReplaySteal):
            print("Stolen from user: {}".format(result.stolen_from.id))
        if(type(result.cheat_type) is Relax):
            print("UR: {}".format(result.ur))
```

(Subject to change) circleguard#run returns a generator that yields each comparison made, regardless of whether it determines it is a cheater or not. Filtering the results afterwards is up to the exact implementation of the script - you can see how we do it in [circleguard](https://github.com/circleguard/circleguard)
