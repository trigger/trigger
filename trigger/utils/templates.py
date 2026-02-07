"""Templating functions for unstructured CLI output."""

from pathlib import Path

from twisted.python import log

from trigger.conf import settings

try:
    import textfsm
except ImportError:
    print("""
    Woops, looks like you're missing the textfsm library.

    Try installing it like this::

        >>> pip install textfsm
    """)

# Exports
__all__ = ("get_template_path", "get_textfsm_object", "load_cmd_template")


def get_template_path(cmd, dev_type=None):
    """Return textfsm templates from the directory pointed to by the TEXTFSM_TEMPLATE_DIR trigger variable.

    :param dev_type: Type of device ie cisco_ios, arista_eos
    :type  dev_type: str
    :param cmd: CLI command to load template.
    :type  cmd: str
    :returns: String template path
    """
    t_dir = settings.TEXTFSM_TEMPLATE_DIR
    return (
        str(
            Path(t_dir) / "{}_{}.template".format(dev_type, cmd.replace(" ", "_")),
        )
        or None
    )


def load_cmd_template(cmd, dev_type=None):
    """:param dev_type: Type of device ie cisco_ios, arista_eos
    :type  dev_type: str
    :param cmd: CLI command to load template.
    :type  cmd: str
    :returns: String template path
    """  # noqa: D205
    try:
        with Path(get_template_path(cmd, dev_type=dev_type)).open("rb") as f:
            return textfsm.TextFSM(f)
    except Exception:
        log.msg(f"Unable to load template:\n{cmd} :: {dev_type}")


def get_textfsm_object(re_table, cli_output):
    """Returns structure object from TextFSM data."""  # noqa: D401
    from collections import defaultdict

    rv = defaultdict(list)
    keys = re_table.header
    values = re_table.ParseText(cli_output)
    pairs = []
    for item in values:
        pairs.extend(zip(map(lambda x: x.lower(), keys), item, strict=False))

    for k, v in pairs:
        rv[k].append(v)

    return dict(rv)
