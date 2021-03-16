# Some consumers may have been relying on imports like
# ``from circleguard.mod import Mod``, even though they should have been using
# ``from circleguard import Mod``. So leave this breadcrumb so those imports
# will still work.
# TODO remove in core 6.0.0
from ossapi import Mod # pylint: disable=unused-import
