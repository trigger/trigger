import unittest
import os
import mock
from trigger.utils.templates import *
from trigger.conf import settings
from contextlib import contextmanager
from StringIO import StringIO
import cStringIO


try:
    import textfsm
except ImportError:
    print("""
    Woops, looks like you're missing the textfsm library.

    Try installing it like this::

        >>> pip install gtextfsm
    """)


cli_data = """*02:00:42.743 UTC Sat Feb 20 2016"""

text_fsm_data = """Value TIME (\d+:\d+:\d+\.\d+)
Value TIMEZONE (\w+)
Value DAYWEEK (\w+)
Value MONTH (\w+)
Value DAY (\d+)
Value YEAR (\d+)

Start
  ^[\*]?${TIME}\s${TIMEZONE}\s${DAYWEEK}\s${MONTH}\s${DAY}\s${YEAR} -> Record
"""

class CheckTemplates(unittest.TestCase):
    """Test structured CLI object data."""

    def setUp(self):
        data = cStringIO.StringIO(text_fsm_data)
        self.re_table = textfsm.TextFSM(data)
        self.assertIsInstance(self.re_table, textfsm.textfsm.TextFSM)

    def testTemplatePath(self):
        """Test that template path is correct."""
        t_path = get_template_path("show clock", dev_type="cisco_ios")
        self.assertIn("vendor/ntc_templates/cisco_ios_show_clock.template", t_path)

    def testGetTextFsmObject(self):
        """Test that we get structured data back from cli output"""
        data = get_textfsm_object(self.re_table, cli_data)
        self.assertIsInstance(data, dict)
        keys = ['dayweek', 'time', 'timezone', 'year', 'day', 'month']
        for key in keys:
            self.assertTrue(data.has_key(key))


if __name__ == "__main__":
    unittest.main()
