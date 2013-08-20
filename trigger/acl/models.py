import datetime
from trigger.conf import settings
import __peewee as pw

engine = settings.DATABASE_ENGINE
if not engine:
    raise RuntimeError('You must specify a database engine in settings.DATABASE_ENGINE')

if engine == 'sqlite3':
    database = pw.SqliteDatabase(database=settings.DATABASE_NAME,
                                 threadlocals=True)
elif engine == 'mysql':
    if not settings.DATABASE_PORT:
        settings.DATABASE_PORT = 3306
    database = pw.MySQLDatabase(host=settings.DATABASE_HOST,
                                database=settings.DATABASE_NAME,
                                port=settings.DATABASE_PORT,
                                user=settings.DATABASE_USER,
                                passwd=settings.DATABASE_PASSWORD,
                                threadlocals=True)
elif engine == 'postgresql':
    database = pw.PostgresqlDatabase(host=settings.DATABASE_HOST,
                                     database=settings.DATABASE_NAME,
                                     port=settings.DATABASE_PORT,
                                     user=settings.DATABASE_USER,
                                     password=settings.DATABASE_PASSWORD,
                                     threadlocals=True)
else:
    raise RuntimeError('Unsupported database engine: %s' % engine)

class BaseModel(pw.Model):
    class Meta:
        database = database

class IntegratedTask(BaseModel):
    """
    Tasks for "integrated" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -l``
    """
    id = pw.PrimaryKeyField()
    acl = pw.CharField(null=False, default='')
    router = pw.CharField(null=False, default='')
    queued = pw.DateTimeField(default=datetime.datetime.now)
    loaded = pw.DateTimeField(null=True)
    escalation = pw.BooleanField(default=False)

    class Meta:
        db_table = 'acl_queue'

class ManualTask(BaseModel):
    """
    Tasks for "manual" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -m``
    """
    q_id = pw.PrimaryKeyField()
    q_ts = pw.DateTimeField(default=datetime.datetime.now)
    q_name = pw.CharField(null=False)
    q_routers = pw.CharField(null=False, default='')
    done = pw.BooleanField(default=False)
    q_sr = pw.IntegerField(null=False, default=0)
    login = pw.CharField(null=False, default='')

    class Meta:
        db_table = 'queue'

MODEL_MAP = {
    'integrated': IntegratedTask,
    'manual': ManualTask,
}

def create_tables():
    """Connect to the database and create the tables for each model."""
    database.connect()
    IntegratedTask.create_table()
    ManualTask.create_table()

def confirm_tables():
    """Ensure the table exists for each model."""
    print 'Checking tables...'
    for q_name, model in MODEL_MAP.iteritems():
        print q_name.ljust(10),
        print model.table_exists()
    else:
        return True
    return False
