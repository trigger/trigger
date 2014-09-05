from trigger.netdevices.loader import BaseLoader
from trigger.exceptions import LoaderFailed
try:
    from pymongo import MongoClient
except ImportError:
    PYMONGO_AVAILABLE = False
else:
    PYMONGO_AVAILABLE = True

class MongoDBLoader(BaseLoader):
    """
    Wrapper for loading metadata via MongoDB.

    To use this define ``NETDEVICES_SOURCE`` in this format::

        mongodb://host:port/?database={database}?table_name={table_name}
    """
    is_usable = PYMONGO_AVAILABLE
 
    def get_data(self, data_source, host, port, database, table_name):
        client = MongoClient(host, port)
        collection = client[database][table_name]
        data = []
        for device in collection.find():
            data.append(device)
        return data
 
    def load_data_source(self, data_source, **kwargs):
        host = kwargs.get('hostname')
        port = kwargs.get('port')
        database = kwargs.get('database')
        table_name = kwargs.get('table_name')
        try:
            return self.get_data(data_source, host, port, database, table_name)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (data_source, err))
