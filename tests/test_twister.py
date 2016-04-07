

import re

import pytest

from trigger.conf import settings


def test_ioslike_prompt_pattern_enabled():
    """Test enabled that IOS-like prompt patterns match correctly."""
    pat = settings.IOSLIKE_PROMPT_PAT

    prompt_tests = [
        'foo-bar1#',
        'foo-bar1# ',
        'foo-bar1(config)# ',
        '\rfoo-bar01(config)# \x08 ',  # "Bonus" backspace in there
        'foo-bar01(config) \r#',  # "Bonus" '\s\r' in there
    ]

    for prompt in prompt_tests:
        assert re.search(pat, prompt) is not None


def test_ioslike_prompt_pattern_nonenabled():
    """Test non-enabled that IOS-like prompt patterns match correctly."""
    pat = settings.IOSLIKE_ENABLE_PAT

    prompt_tests = [
        'foo-bar1>',
        'foo-bar1> ',
        '\rfoo-bar01)> \x08 ',  # "Bonus" backspace in there
        'foo-bar01) \r>',  # "Bonus" '\s\r' in there
    ]

    for prompt in prompt_tests:
        assert re.search(pat, prompt) is not None
