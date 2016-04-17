
import datetime
from pytz import timezone
from trigger.utils import cli
from trigger.utils.network import ping


def test_pretty_time():
    """Test that ``pretty_time`` works()."""
    now = datetime.datetime.now(timezone('US/Pacific'))
    tomorrow = now + datetime.timedelta(days=1)
    pretty = cli.pretty_time(tomorrow)
    assert 'tomorrow' in pretty

def test_ping():
    """Validate network.ping functionality"""
    assert ping("localhost")
    assert not ping("unresolvable_test_host")
