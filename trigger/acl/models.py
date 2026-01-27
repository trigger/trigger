"""
Database models for the task queue.
"""

import datetime
from trigger.conf import settings
import peewee as pw

engine = settings.DATABASE_ENGINE
if not engine:
    raise RuntimeError("You must specify a database engine in settings.DATABASE_ENGINE")

# We're hard-coding support for the BIG THREE database solutions for now,
# because that's what the ``peewee`` library we are using as the ORM supports.
if engine == "sqlite3":
    database = pw.SqliteDatabase(database=settings.DATABASE_NAME)
elif engine == "mysql":
    if not settings.DATABASE_PORT:
        settings.DATABASE_PORT = 3306
    database = pw.MySQLDatabase(
        host=settings.DATABASE_HOST,
        database=settings.DATABASE_NAME,
        port=settings.DATABASE_PORT,
        user=settings.DATABASE_USER,
        passwd=settings.DATABASE_PASSWORD,
    )
elif engine == "postgresql":
    database = pw.PostgresqlDatabase(
        host=settings.DATABASE_HOST,
        database=settings.DATABASE_NAME,
        port=settings.DATABASE_PORT,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
    )
else:
    raise RuntimeError("Unsupported database engine: %s" % engine)


class BaseModel(pw.Model):
    """
    Base model that inherits the database object determined above.
    """

    class Meta:
        database = database


class CustomCharField(pw.CharField):
    """Overload default CharField to always return strings vs. UTF-8"""

    def coerce(self, value):
        return str(value or "")


class IntegratedTask(BaseModel):
    """
    Tasks for "integrated" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -l``
    """

    # Python 3 / peewee v3+: PrimaryKeyField renamed to AutoField
    id = pw.AutoField()
    acl = CustomCharField(null=False, default="")
    router = CustomCharField(null=False, default="")
    queued = pw.DateTimeField(default=datetime.datetime.now)
    loaded = pw.DateTimeField(null=True)
    escalation = pw.BooleanField(default=False)

    class Meta:
        # Python 3 / peewee v3+: db_table renamed to table_name
        table_name = "acl_queue"


class ManualTask(BaseModel):
    """
    Tasks for "manual" queue used by `~trigger.acl.queue.Queue`.

    e.g. ``acl -m``
    """

    q_id = pw.AutoField()
    q_ts = pw.DateTimeField(default=datetime.datetime.now)
    q_name = CustomCharField(null=False)
    q_routers = CustomCharField(null=False, default="")
    done = pw.BooleanField(default=False)
    q_sr = pw.IntegerField(null=False, default=0)
    login = CustomCharField(null=False, default="")

    class Meta:
        table_name = "queue"


MODEL_MAP = {
    "integrated": IntegratedTask,
    "manual": ManualTask,
}


def create_tables():
    """Connect to the database and create the tables for each model."""
    database.connect()
    IntegratedTask.create_table()
    ManualTask.create_table()


def confirm_tables():
    """Ensure the table exists for each model."""
    print("Checking tables...")
    width = max(len(q_name) for q_name in MODEL_MAP)
    for q_name, model in MODEL_MAP.items():
        print(q_name.ljust(width), end=" ")
        print(model.table_exists())
    else:
        return True
    return False
