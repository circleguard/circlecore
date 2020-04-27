class CircleguardException(Exception):
    """Base class for exceptions in the circleguard program."""

class InvalidArgumentsException(CircleguardException):
    """Indicates an invalid argument was passed to one of the flags."""

class APIException(CircleguardException):
    """
    Indicates an error involving the API, which may or may not be fatal.

    UnknownAPIExceptions are considered fatal, InternalAPIExceptions are not.
    """

class NoInfoAvailableException(APIException):
    """Indicates that the API returned no information for the given arguments"""

class UnknownAPIException(APIException):
    """Indicates some error on the API's end that we were not prepared to handle."""

class InternalAPIException(APIException):
    """Indicates a response from the API that we know how to handle."""

class InvalidKeyException(InternalAPIException):
    """Indicates that an api key was rejected by the api."""

class RatelimitException(InternalAPIException):
    """Indicates that our key has been ratelimited and we should retry the request at a later date."""

class InvalidJSONException(InternalAPIException):
    """Indicates that the api returned an invalid json response, and we should retry the request."""

class ReplayUnavailableException(InternalAPIException):
    """Indicates that we expected a replay from the api but it was not able to deliver it."""
