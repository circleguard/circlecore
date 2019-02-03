class CircleguardException(Exception):
    """Base class for exceptions in the Circleguard program."""

class InvalidArgumentsException(CircleguardException):
    """Indicates an invalid argument was passed to one of the flags."""

class APIException(CircleguardException):
    """Indicates some error on the API's end that we were not prepared to handle."""
