"""Python Webhook and Event Framework."""
from __future__ import absolute_import, unicode_literals

import re

from collections import namedtuple

from .app import Thorn
from .events import Event, ModelEvent
from .decorators import webhook_model
from .reverse import model_reverser
from .utils.functional import Q
from ._state import buffer_events


__version__ = '1.5.0'
__author__ = 'Robinhood Markets'
__contact__ = 'thorn@robinhood.com'
__homepage__ = 'http://github.com/robinhood/thorn'
__docformat__ = 'restructuredtext'

# -eof meta-

version_info_t = namedtuple('version_info_t', (
    'major', 'minor', 'micro', 'releaselevel', 'serial',
))

# bumpversion can only search for {current_version}
# so we have to parse the version here.
_temp = re.match(
    r'(\d+)\.(\d+).(\d+)(.+)?', __version__).groups()
VERSION = version_info = version_info_t(
    int(_temp[0]), int(_temp[1]), int(_temp[2]), _temp[3] or '', '')
del(_temp)
del(re)

__all__ = [
    'Thorn', 'Event', 'ModelEvent',
    'Q', 'model_reverser', 'webhook_model', 'buffer_events',
]
