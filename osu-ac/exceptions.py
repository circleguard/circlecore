class AnticheatException(Exception):
    """Base class for exceptions in the anticheat program."""

class InvalidArgumentsException(AnticheatException):
    """Indicates an invalid argument was passed to one of the flags."""

class APIException(AnticheatException):
    """Indicates some error on the API's end that we were not prepared to handle."""
