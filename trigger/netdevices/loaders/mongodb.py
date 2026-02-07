"""NetDevices loader for MongoDB-backed device metadata."""

from trigger.exceptions import LoaderFailed
from trigger.netdevices.loader import BaseLoader

try:
    from pymongo import MongoClient
except ImportError:
    PYMONGO_AVAILABLE = False
else:
    PYMONGO_AVAILABLE = True


class MongoDBLoader(BaseLoader):
    """Wrapper for loading metadata via MongoDB.

    To use this define ``NETDEVICES_SOURCE`` in this format::

        mongodb://host:port/?database={database}?table_name={table_name}
    """

    is_usable = PYMONGO_AVAILABLE

    def get_data(self, data_source, host, port, database, table_name):  # noqa: D102
        client = MongoClient(host, port)
        collection = client[database][table_name]
        return list(collection.find())

    def load_data_source(self, data_source, **kwargs):  # noqa: D102
        host = kwargs.get("hostname")
        port = kwargs.get("port")
        database = kwargs.get("database")
        table_name = kwargs.get("table_name")
        try:
            return self.get_data(data_source, host, port, database, table_name)
        except Exception as err:
            msg = f"Tried {data_source!r}; and failed: {err!r}"
            raise LoaderFailed(msg) from err
