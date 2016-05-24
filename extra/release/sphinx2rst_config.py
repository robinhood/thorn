from __future__ import absolute_import, unicode_literals

rtd_base = 'http://thorn.readthedocs.io/en/latest'


def rtd(*path):
    return '/'.join((rtd_base,) + path)

REFBASE = 'http://docs.celeryproject.org/en/latest'
REFS = {
    'mailing-list':
        'http://groups.google.com/group/thorn-users',
    'irc-channel': 'getting-started/resources.html#irc',
    'events-guide': rtd('userguide/events.html'),
    'reporting-bugs': 'contributing.html#reporting-bugs',
}
