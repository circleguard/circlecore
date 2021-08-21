# this file is left as an alias so that we can pretend the Mod class comes from
# circlecore, even though we're really using ossapi's Mod class. The Mod class
# used to live in circlecore so consumers may have imported it directly, so
# this linkage needs to exist at least until core 6.0.0. After that we can
# reassess whether it makes sense to leave this or convert our mod imports to
# import from ossapi instead. I think we will want to convert them, but a
# problem for future me.
from ossapi.mod import ModCombination, Mod # pylint: disable=unused-import
