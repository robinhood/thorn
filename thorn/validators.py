from __future__ import absolute_import, unicode_literals

import socket

from ipaddress import ip_address, ip_network
from six import text_type

from kombu.utils.url import urlparse

from .exceptions import SecurityError

__all__ = [
    'ensure_protocol', 'ensure_port',
    'block_internal_ips', 'block_cidr_network',
]

validators = {}


def validator(fun):
    """Make validator json serializable."""
    validators[fun.__name__] = fun
    return fun


def serialize_validator(v):
    return (v._validator, v._args)


def deserialize_validator(v):
    if isinstance(v, (list, tuple)):
        name, args = v
        return validators[name](*args)
    return v


def _is_internal_address(addr):
    return any([
        addr.is_private,
        addr.is_reserved,
        addr.is_loopback,
        addr.is_multicast,
    ])


@validator
def ensure_protocol(*allowed):
    """Only allow recipient URLs using specific protocols.

    Example:
        ensure_protocol('https', 'http://')

    """
    allowed = tuple(
        x if '://' in x else x + '://'
        for x in allowed
    )

    def validate_protocol(recipient_url):
        if not recipient_url.startswith(allowed):
            raise SecurityError(
                'Protocol of recipient URL not allowed ({0} only)'.format(
                    allowed))
    validate_protocol._args = allowed
    validate_protocol._validator = 'ensure_protocol'
    return validate_protocol


@validator
def ensure_port(*allowed):
    allowed = tuple(int(p) for p in allowed)

    def validate_port(recipient_url):
        port = urlparse(recipient_url).port
        if port and int(port) not in allowed:
            raise SecurityError(
                'Port of recipient URL {0} not allowed ({1} only)'.format(
                    recipient_url, allowed))
    validate_port._args = allowed
    validate_port._validator = 'ensure_port'
    return validate_port


def _url_ip_address(url):
    try:
        return ip_address(text_type(url))
    except ValueError:
        host = urlparse(url).hostname
        return ip_address(text_type(socket.gethostbyname(host)))


@validator
def block_internal_ips():
    """Block recipient URLs that have an internal IP address.

    .. warning::

        This does not check for *private* networks, it will only
        make sure the IP address is not in a reserved private block
        (e.g. 192.168.0.1/24).

    """

    def validate_not_internal_ip(recipient_url):
        addr = _url_ip_address(recipient_url)
        if _is_internal_address(addr):
            raise SecurityError(
                'IP address of recipient {0}={1} considered private!'.format(
                    recipient_url, addr))
    validate_not_internal_ip._args = ()
    validate_not_internal_ip._validator = 'block_internal_ips'
    return validate_not_internal_ip


@validator
def block_cidr_network(*blocked_networks):
    """Block recipient URLs from a list of CIDR networks.

    Example:

        block_cidr_network('192.168.0.0/24', '132.34.23.0/24')

    """
    _blocked_networks = [ip_network(text_type(x)) for x in blocked_networks]

    def validate_cidr(recipient_url):
        recipient_addr = _url_ip_address(recipient_url)
        for blocked_network in _blocked_networks:
            if recipient_addr in blocked_network:
                raise SecurityError(
                    'IP address of recipient {0}={1} is in network {2}'.format(
                        recipient_url, recipient_addr, blocked_network,
                    ))
    validate_cidr._args = blocked_networks
    validate_cidr._validator = 'block_cidr_network'
    return validate_cidr
