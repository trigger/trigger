"""
Built-in Loader objects for loading `~trigger.netdevices.NetDevice` metadata
from the filesystem.
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2013, AOL Inc.'
__version__ = '1.1'

import itertools
import os
from trigger.conf import settings
from trigger.netdevices.loader import BaseLoader
from trigger import exceptions, rancid
from trigger.exceptions import LoaderFailed
try:
    import simplejson as json # Prefer simplejson because of SPEED!
except ImportError:
    import json
import xml.etree.cElementTree as ET

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

class JSONLoader(BaseLoader):
    """
    Wrapper for loading metadata via JSON from the filesystem.

    Parse 'netdevices.json' and return list of JSON objects.
    """
    is_usable = True

    def get_data(self, data_source):
        with open(data_source, 'r') as contents:
            # TODO (jathan): Can we somehow return an generator like the other
            # _parse methods? Maybe using JSONDecoder?
            data = json.load(contents)
        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class XMLLoader(BaseLoader):
    """
    Wrapper for loading metadata via XML from the filesystem.

    Parse 'netdevices.xml' and return a list of node 2-tuples (key, value).
    These are as good as a dict without the extra dict() call.
    """
    is_usable = True

    def get_data(self, data_source):
        #Parsing the complete file into a tree once and extracting outthe
        # device nodes is faster than using iterparse(). Curses!!
        xml = ET.parse(data_source).findall('device')

        # This is a generator within a generator. Trust me, it works in _populate()
        data = (((e.tag, e.text) for e in node.getchildren()) for node in xml)

        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class RancidLoader(BaseLoader):
    """
    Wrapper for loading metadata via RANCID from the filesystem.

    Parse RANCID's ``router.db`` and return a generator of node 2-tuples (key,
    value).
    """
    is_usable = True

    def get_data(self, data_source, recurse_subdirs=None):
        data = rancid.parse_rancid_data(data_source,
                                        recurse_subdirs=recurse_subdirs)
        return data

    def load_data_source(self, data_source, **kwargs):
        # We want to make sure that we've set this variable
        recurse_subdirs = kwargs.get('recurse_subdirs',
                                     settings.RANCID_RECURSE_SUBDIRS)
        try:
            return self.get_data(data_source, recurse_subdirs)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class SQLiteLoader(BaseLoader):
    """
    Wrapper for loading metadata via SQLite from the filesystem.

    Parse 'netdevices.sql' and return a list of stuff.
    """
    is_usable = SQLITE_AVAILABLE

    def get_data(self, data_source, table_name='netdevices'):
        connection = sqlite3.connect(data_source)
        cursor = connection.cursor()

        # Get the column names. This is a simple list strings.
        colfetch  = cursor.execute('pragma table_info(%s)' % table_name)
        results = colfetch.fetchall()
        columns = [r[1] for r in results]

        # And the devices. This is a list of tuples whose values match the indexes
        # of the column names.
        devfetch = cursor.execute('select * from %s' % table_name)
        devrows = devfetch.fetchall()

        # Another generator within a generator, which structurally is a list of
        # lists containing 2-tuples (key, value).
        data = (itertools.izip(columns, row) for row in devrows)

        return data

    def load_data_source(self, data_source, **kwargs):
        table_name = kwargs.get('table_name', 'netdevices')
        try:
            return self.get_data(data_source, table_name)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))

class CSVLoader(BaseLoader):
    """
    Wrapper for loading metadata via CSV from the filesystem.

    This leverages the functionality from the `~trigger.rancid`` library.

    At the bare minimum your CSV file must be populated with 2-tuples of
    "nodeName,manufacturer" (e.g. "test1-abc.net.aol.com,cisco"), separated by
    newlines. The ``deviceType`` will default to whatever is specified in
    :settings:`FALLBACK_TYPE` and ``deviceStatus`` will default to "up"
    ("PRODUCTION").

    At max you may provide "nodeName,vendor,deviceStatus,deviceType" just like
    what you'd expect from RANCID's ``router.db`` file format.
    """
    is_usable = True

    def get_data(self, data_source):
        root_dir, filename = os.path.split(data_source)
        data = rancid.parse_rancid_file(root_dir, filename, delimiter=',')
        return data

    def load_data_source(self, data_source, **kwargs):
        try:
            return self.get_data(data_source)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))
