"""
Utilities for parsing/handling URLs
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2013, AOL Inc.'
__version__ = '0.1'

from urllib import unquote
from urlparse import urlparse
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

def _parse_url(url):
    """
    Guts for `~trigger.utils.url.parse_url`.

    Based on Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH
    """
    parts = urlparse(url)
    scheme = parts.scheme
    port = parts.port or None
    hostname = parts.hostname
    path = parts.path or ''
    virtual_host = path[1:] if path and path[0] == '/' else path
    return (scheme, unquote(hostname or '') or None, port,
            unquote(parts.username or '') or None,
            unquote(parts.password or '') or None,
            unquote(path or '') or None,
            unquote(virtual_host or '') or None,
            unquote(parts.query or '') or None,
            dict(dict(parse_qsl(parts.query))))

def parse_url(url):
    """
    Given a ``url`` returns, a dict of its constituent parts.

    Based on Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH

    :param url:
        Any standard URL. (file://, https://, etc.)
    """
    scheme, host, port, user, passwd, path, vhost, qs, qs_dict = _parse_url(url)
    return dict(scheme=scheme, hostname=host, port=port, username=user,
                password=passwd, path=path, virtual_host=vhost,
                query=qs, **qs_dict)

if __name__ == '__main__':
    tests = (
        "https://username:password@myhost.aol.com:12345?limit=10&vendor=cisco#develop",
        "file:///usr/local/etc/netdevices.xml",
        '/usr/local/etc/netdevices.xml',
        'mysql://dbuser:dbpass@dbhost.com:3306/',
        'http://jathan:password@api.foo.com/netdevices/?limit=10&device_type=switch&vendor=cisco&format=json',
    )

    import pprint
    for test in tests:
        print test
        pprint.pprint(parse_url(test))
        print
