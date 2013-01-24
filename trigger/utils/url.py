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
    Stub for `~trigger.utils.url.parse_url`

    Borrowed from Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH
    """
    scheme = urlparse(url).scheme
    schemeless = url[len(scheme) + 3:]
    # parse with HTTP URL semantics
    parts = urlparse('http://' + schemeless)

    port = parts.port or None
    hostname = parts.hostname
    path = parts.path or ''
    path = path[1:] if path and path[0] == '/' and scheme != 'file' else path
    virtual_host = path[1:] if path and path[0] == '/' else path
    return (scheme, unquote(hostname or '') or None, port,
            unquote(parts.username or '') or None,
            unquote(parts.password or '') or None,
            unquote(path or '') or None,
            unquote(virtual_host or '') or None,
            dict(dict(parse_qsl(parts.query))))

def parse_url(url):
    """
    Given a ``url`` returns, a dict of its constituent parts.

    Borrowed from Kombu's ``kombu.utils.url``.
    Source: http://bit.ly/11UFcfH

    :param url:
        Any standard URL. (file://, https://, etc.)
    """
    scheme, host, port, user, password, path, virtual_host, query = _parse_url(url)
    return dict(transport=scheme, hostname=host,
                port=port, userid=user,
                password=password, path=path, virtual_host=virtual_host, **query)

if __name__ == '__main__':
    tests = (
        "https://username:password@myhost.aol.com:12345?limit=10&vendor=cisco#develop",
        "file:///usr/local/etc/netdevices.xml",
    )

    import pprint
    for test in tests:
        print test
        pprint.pprint(parse_url(test))
        print
