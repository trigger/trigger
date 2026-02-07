import re

import pytest

from trigger.conf import settings
from trigger.twister import compile_prompt_pattern, prompt_match_start


def test_ioslike_prompt_pattern_enabled():
    """Test enabled that IOS-like prompt patterns match correctly."""
    pat = settings.IOSLIKE_PROMPT_PAT

    prompt_tests = [
        "foo-bar1#",
        "foo-bar1# ",
        "foo-bar1(config)# ",
        "\rfoo-bar01(config)# \x08 ",  # "Bonus" backspace in there
        "foo-bar01(config) \r#",  # "Bonus" '\s\r' in there
    ]

    for prompt in prompt_tests:
        assert re.search(pat, prompt) is not None


def test_ioslike_prompt_pattern_nonenabled():
    """Test non-enabled that IOS-like prompt patterns match correctly."""
    pat = settings.IOSLIKE_ENABLE_PAT

    prompt_tests = [
        "foo-bar1>",
        "foo-bar1> ",
        "\rfoo-bar01)> \x08 ",  # "Bonus" backspace in there
        "foo-bar01) \r>",  # "Bonus" '\s\r' in there
    ]

    for prompt in prompt_tests:
        assert re.search(pat, prompt) is not None


# =============================================================================
# False-positive prevention tests (Issue #317)
# =============================================================================


class TestFalsePositivePrevention:
    """Verify that command output containing '>' or '#' is NOT matched as a prompt."""

    def test_juniper_rsync_flag_not_matched(self):
        """Juniper 'Flags: <Sync RSync>' must not match as a prompt (issue #317)."""
        pat = compile_prompt_pattern(settings.PROMPT_PATTERNS["juniper"])
        buffer = "Flags: <Sync RSync>\r\n"
        assert pat.search(buffer) is None

    def test_ioslike_comment_not_matched(self):
        """A '# comment' line must not match IOS-like prompt pattern."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "some output\r\n# This is a comment in output\r\n"
        assert pat.search(buffer) is None

    def test_enable_angle_bracket_not_matched(self):
        """A '>' inside command output must not match the enable pattern."""
        pat = compile_prompt_pattern(settings.IOSLIKE_ENABLE_PAT)
        buffer = "Description: Traffic >1Gbps\r\nMore output here\r\n"
        assert pat.search(buffer) is None

    def test_ioslike_prompt_mid_line_not_matched(self):
        """IOS-like prompt pattern should not match '#' in the middle of a line."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "some leading text device-name# "
        assert pat.search(buffer) is None

    def test_juniper_xml_angle_bracket_not_matched(self):
        """Juniper XML output with '>' should not match as prompt."""
        pat = compile_prompt_pattern(settings.PROMPT_PATTERNS["juniper"])
        buffer = '<rpc-reply xmlns:junos="http://xml.juniper.net">\r\n'
        assert pat.search(buffer) is None


# =============================================================================
# Valid prompt regression tests
# =============================================================================


class TestValidPromptMatching:
    """Verify that real prompts still match correctly after the anchoring fix."""

    def test_first_prompt_no_preceding_newline(self):
        """A prompt at the very start of the buffer (no preceding newline) must match."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "router1# "
        m = pat.search(buffer)
        assert m is not None

    def test_prompt_after_newline(self):
        """A prompt after \\n must match."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "some output\nrouter1# "
        m = pat.search(buffer)
        assert m is not None
        assert prompt_match_start(m) == len("some output\n")

    def test_prompt_after_crlf(self):
        """A prompt after \\r\\n must match."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "some output\r\nrouter1# "
        m = pat.search(buffer)
        assert m is not None
        assert prompt_match_start(m) == len("some output\r\n")

    def test_juniper_prompt_after_master_banner(self):
        """Juniper prompt after {master} banner must match."""
        pat = compile_prompt_pattern(settings.PROMPT_PATTERNS["juniper"])
        buffer = "{master}\nuser@router> "
        m = pat.search(buffer)
        assert m is not None

    def test_ioslike_config_mode_prompt(self):
        """IOS config mode prompt must match."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "output line\nswitch1(config)# "
        m = pat.search(buffer)
        assert m is not None

    def test_enable_prompt_at_start(self):
        """Enable prompt at start of buffer must match."""
        pat = compile_prompt_pattern(settings.IOSLIKE_ENABLE_PAT)
        buffer = "router1> "
        m = pat.search(buffer)
        assert m is not None
        assert prompt_match_start(m) == 0

    def test_paloalto_prompt_with_crlf(self):
        """Palo Alto prompt with \\r\\n prefix must match."""
        pat = compile_prompt_pattern(settings.PROMPT_PATTERNS["paloalto"])
        buffer = "output\r\nadmin@fw1> "
        m = pat.search(buffer)
        assert m is not None


# =============================================================================
# prompt_match_start correctness tests
# =============================================================================


class TestPromptMatchStart:
    """Verify prompt_match_start returns the correct index."""

    def test_match_at_buffer_start(self):
        """Match at buffer start returns 0."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "router1# "
        m = pat.search(buffer)
        assert m is not None
        assert prompt_match_start(m) == 0

    def test_match_after_lf(self):
        """Match after \\n skips the newline character."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "output\nrouter1# "
        m = pat.search(buffer)
        assert m is not None
        # The \n is at index 6, prompt starts at index 7
        assert prompt_match_start(m) == 7

    def test_match_after_crlf(self):
        """Match after \\r\\n skips both characters."""
        pat = compile_prompt_pattern(settings.IOSLIKE_PROMPT_PAT)
        buffer = "output\r\nrouter1# "
        m = pat.search(buffer)
        assert m is not None
        # \r at 6, \n at 7, prompt starts at 8
        assert prompt_match_start(m) == 8


# =============================================================================
# compile_prompt_pattern behavior tests
# =============================================================================


class TestCompilePromptPattern:
    """Verify compile_prompt_pattern handles various inputs correctly."""

    def test_already_compiled_pattern_returned_unchanged(self):
        """An already-compiled re.Pattern should be returned as-is."""
        compiled = re.compile(r"foo#\s?$")
        result = compile_prompt_pattern(compiled)
        assert result is compiled

    def test_pattern_starting_with_caret_not_double_anchored(self):
        """A pattern starting with ^ should not get a redundant prefix."""
        pat = compile_prompt_pattern(r"^\S+#\s?$")
        assert pat.search("router1# ") is not None
        # Verify no double-anchor by checking pattern string
        assert not pat.pattern.startswith(r"(?:^|\r?\n)^")

    def test_pattern_starting_with_backslash_r_not_prefixed(self):
        """A pattern starting with \\r should not get a prefix (e.g. paloalto)."""
        pat = compile_prompt_pattern(r"\r\n\S+(?:\>|#)\s?$")
        # Pattern should still work
        assert pat.search("\r\nadmin@fw1> ") is not None
        # Verify no prefix added
        assert not pat.pattern.startswith(r"(?:^|\r?\n)\r")

    def test_pattern_starting_with_backslash_n_not_prefixed(self):
        """A pattern starting with \\n should not get a prefix."""
        pat = compile_prompt_pattern(r"\n\S+#\s?$")
        assert not pat.pattern.startswith(r"(?:^|\r?\n)\n")

    def test_multiline_flag_is_set(self):
        """The compiled pattern should have re.MULTILINE enabled."""
        pat = compile_prompt_pattern(r"\S+#\s?$")
        assert pat.flags & re.MULTILINE


# =============================================================================
# Parametrized vendor pattern tests
# =============================================================================


# Map each vendor pattern to a sample prompt that should match on its own line
VENDOR_PROMPT_SAMPLES = {
    "aruba": "(Aruba7010) #",
    "avocent": "admin-0->",
    "citrix": " Done\n",
    "cumulus": "cumulus@switch# ",
    "f5": "admin@(bigip1)(cfg-sync Standalone)(Active)(/Common)(tmos)# ",
    "juniper": "user@router> ",
    "mrv": "\r\nMRV OptiSwitch 1 >>",
    "netscreen": "fw1-> ",
    "paloalto": "\r\nadmin@fw1> ",
    "pica8": "admin@switch> ",
}


@pytest.mark.parametrize(
    ("vendor", "sample_prompt"),
    list(VENDOR_PROMPT_SAMPLES.items()),
    ids=list(VENDOR_PROMPT_SAMPLES.keys()),
)
def test_vendor_pattern_matches_sample_prompt(vendor, sample_prompt):
    """Each vendor pattern must match its expected sample prompt."""
    pat = compile_prompt_pattern(settings.PROMPT_PATTERNS[vendor])
    assert pat.search(sample_prompt) is not None, (
        f"Vendor {vendor!r} pattern failed to match sample prompt {sample_prompt!r}"
    )


@pytest.mark.parametrize(
    "vendor",
    list(settings.PROMPT_PATTERNS.keys()),
)
def test_vendor_pattern_compiles_without_error(vendor):
    """Every vendor pattern in PROMPT_PATTERNS must compile successfully."""
    pat = compile_prompt_pattern(settings.PROMPT_PATTERNS[vendor])
    assert isinstance(pat, re.Pattern)
