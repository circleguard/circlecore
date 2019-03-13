import types
from circleguard import config

class Check():
    def __init__(self, uid=None, u2id=None, mid=None, num=config.num, mods=None, threshold=config.thresh, stddevs=config.stddevs, silent=config.silent):
        self.user_id = uid
        self.user2_id = u2id
        self.map_id = mid
        self.num = num
        self.mods = mods
        self.threshold = threshold
        self.stddevs = stddevs
        self.silent = silent


class MapCheck(Check):
    def __init__(self, map_id, user_id=None, num=config.num, mods=None, threshold=config.thresh, stddevs=None):
        Check.__init__(self, uid=user_id, mid=map_id, num=num, mods=flist(mods), threshold=threshold, stddevs=stddevs)

class UsersAgainstMap(MapCheck):
    def __init__(self, map_id, user_id, num=config.num, mods=None, threshold=config.thresh, stddevs=None):
        Check.__init__(self, uid=user_id, mid=map_id, num=num, mods=flist(mods), threshold=threshold, stddevs=stddevs)


class VerifyCheck(Check):
     def __init__(self, map_id, user_id, user2_id, num=config.num, mods=None, threshold=config.thresh, stddevs=None):
        Check.__init__(self, uid=user_id, u2id=user2_id, num=num, mid=map_id, mods=flist(mods), threshold=threshold, stddevs=stddevs)

def flist(obj):
    """
    ('force list')
    Returns a new list of the given object if it is neither a string nor an iterable, and
    returns the object if it is.
    """
    if not (isinstance(obj, str) or hasattr(obj, "__iter__")):
        return [obj]
    return obj
