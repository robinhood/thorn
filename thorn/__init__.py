"""Python Webhook and Event Framework"""
from __future__ import absolute_import, unicode_literals

from .app import Thorn
from .events import Event, ModelEvent
from .decorators import webhook_model
from .reverse import model_reverser
from .utils.functional import Q


VERSION = (1, 1, 0)
__version__ = '.'.join(map(str, VERSION[0:3])) + ''.join(VERSION[3:])
__author__ = 'Robinhood Markets'
__contact__ = 'thorn@robinhood.com'
__homepage__ = 'http://github.com/robinhood/thorn'
__docformat__ = 'restructuredtext'

# -eof meta-

__all__ = [
    'Thorn', 'Event', 'ModelEvent',
    'Q', 'model_reverser', 'webhook_model',
]
