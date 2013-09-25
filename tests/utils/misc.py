# -*- coding: utf-8 -*-

"""
Misc. utils for testing.
"""

from contextlib import contextmanager
from StringIO import StringIO
import sys

__all__ = ('captured_output',)

@contextmanager
def captured_output():
    """
    A context manager to capture output from things that print so you can
    compare them!

    Use it like this::

        with captured_output() as (out, err):
            foo()
        # This can go inside or outside the `with` block
        output = out.getvalue().strip()
        self.assertEqual(output, 'hello world!')

    Credit: Rob Kennedy
    Source: http://stackoverflow.com/a/17981937/194311
    """
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err
