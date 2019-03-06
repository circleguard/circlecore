from exceptions import InvalidArgumentsException
from enums import Mod

def mod_to_int(mod):
    """
    Returns the integer representation of a mod string. The mods in the string can be in any order -
    "HDDT" will be parsed the same as "DTHD".

    Args:
        String mod: The modstring to convert.

    Returns:
        The integer representation of the passed mod string.

    """

    mod_total = 0
    for acronym in [mod[i:i+2] for i in range(0, len(mod), 2)]:
        mod_total += Mod[acronym].value

    return mod_total
