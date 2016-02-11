import unittest
import os
import mock
from trigger.utils.templates import _template_path
from trigger.conf import settings
from contextlib import contextmanager
from StringIO import StringIO


try:
    import textfsm
except ImportError:
    print("""
    Woops, looks like you're missing the textfsm library.

    Try installing it like this::

        >>> pip install gtextfsm
    """)


text_fsm_data = """Value TIME (\d+:\d+:\d+\.\d+)
Value TIMEZONE (\w+)
Value DAYWEEK (\w+)
Value MONTH (\w+)
Value DAY (\d+)
Value YEAR (\d+)

Start
  ^[\*]?${TIME}\s${TIMEZONE}\s${DAYWEEK}\s${MONTH}\s${DAY}\s${YEAR} -> Record
"""


class CheckCliData(unittest.TestCase):
    """Test structured CLI object data."""

    def testTemplatePath(self):
        """Test that template path is correct."""
        t_path = _template_path("cisco_ios", "show clock")
        self.assertIn("vendor/ntc_templates/cisco_ios_show_clock.template", t_path)

    # def testCliToDict(self):
        # with mock.patch('__builtin__.open') as my_mock:
            # my_mock.return_value.__enter__ = lambda s: s
            # my_mock.return_value.__exit__ = mock.Mock()
            # my_mock.return_value.read.return_value = text_fsm_data
            # with open('foo') as h:
                # re_table = textfsm.TextFSM(h)
                # fsm_results = 



if __name__ == "__main__":
    unittest.main()
