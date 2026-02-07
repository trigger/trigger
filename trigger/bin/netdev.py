#!/usr/bin/env python

"""netdev - Command-line search interface for NetDevices."""

__version__ = "1.2"

import sys
from optparse import OptionParser

from trigger.netdevices import NetDevices, device_match


def parse_args(argv):
    """Parse arguments, duh. There is a better way to do this using Twisted's
    usage module, but replacing it is not a high priority.
    """
    parser = OptionParser(
        usage="%prog [options]",
        description="\nCommand-line search interface for 'NetDevices' metadata.",
        version="%prog " + __version__,
    )

    parser.add_option(
        "-a",
        "--acls",
        action="store_true",
        help="Search will return acls instead of devices.",
    )
    parser.add_option(
        "-l",
        "--list",
        type="string",
        metavar="<DEVICE>",
        help="List all information for individual DEVICE",
    )
    parser.add_option(
        "-s",
        "--search",
        action="store_true",
        help="Perform a search based on matching criteria",
    )
    parser.add_option(
        "-L",
        "--location",
        type="string",
        metavar="<LOCATION>",
        help="For use with -s:  Match on site location.",
    )
    parser.add_option(
        "-n",
        "--nodename",
        type="string",
        metavar="<NODENAME>",
        help="For use with -s:  Match on full or partial nodeName.  NO REGEXP.",
    )
    parser.add_option(
        "-t",
        "--type",
        type="string",
        metavar="<TYPE>",
        help="For use with -s:  Match on deviceType.  Must be FIREWALL, ROUTER, or SWITCH.",
    )
    parser.add_option(
        "-o",
        "--owning-team",
        type="string",
        metavar="<OWNING TEAM NAME>",
        help="For use with -s:  Match on Owning Team (owningTeam).",
    )
    parser.add_option(
        "-O",
        "--oncall-team",
        type="string",
        metavar="<ONCALL TEAM NAME>",
        help="For use with -s:  Match on Oncall Team (onCallName).",
    )
    parser.add_option(
        "-C",
        "--owning-org",
        type="string",
        metavar="<OWNING ORG>",
        help="For use with -s:  Match on cost center Owning Org. (owner).",
    )
    parser.add_option(
        "-v",
        "--vendor",
        type="string",
        metavar="<VENDOR>",
        help="For use with -s:  Match on canonical vendor name.",
    )
    parser.add_option(
        "-m",
        "--manufacturer",
        type="string",
        metavar="<MANUFACTURER>",
        help="For use with -s:  Match on manufacturer.",
    )
    parser.add_option(
        "-b",
        "--budget-code",
        type="string",
        metavar="<BUDGET CODE>",
        help="For use with -s:  Match on budget code",
    )
    parser.add_option(
        "-B",
        "--budget-name",
        type="string",
        metavar="<BUDGET NAME>",
        help="For use with -s:  Match on budget name",
    )
    parser.add_option(
        "-k",
        "--make",
        type="string",
        metavar="<MAKE>",
        help="For use with -s:  Match on make.",
    )
    parser.add_option(
        "-M",
        "--model",
        type="string",
        metavar="<MODEL>",
        help="For use with -s:  Match on model.",
    )
    parser.add_option(
        "-c",
        "--coordinate",
        type="string",
        metavar="<COORDINATE>",
        help="For use with -s:  Match on coordinate (rack number).",
    )
    parser.add_option(
        "-N",
        "--nonprod",
        action="store_false",
        default=True,
        help="Look for production and non-production devices.",
    )
    # parser.add_option('-A', '--aclname', action='append', default=[],
    #    help='For use with -s:  Match on acl filter name. You may add multiple.')

    opts, args = parser.parse_args(argv)

    if opts.list and opts.search:
        parser.error("-l and -s cannot be used together")

    # Turn opts.list into NetDevice object
    if opts.list:
        dev = device_match(opts.list.lower(), production_only=opts.nonprod)
        if not dev:
            sys.exit(1)
        dev.dump()

    if not opts.list and not opts.search:
        parser.print_help()
        parser.error("must choose either -l or -s (but not both!)")
        sys.exit(1)

    if opts.search:
        # Get a list of search options, stripping out modifiers. This makes us
        # resilient to adding new arguments without having to explicitly check
        # for them by name, so long as they aren't one of the modifying opts.
        # If you add a Boolean option, add it to skip_opts.
        skip_opts = ("list", "search", "help", "acls", "nonprod")
        search_opts = [x for x in sorted(opts.__dict__) if x not in skip_opts]
        oget = opts.__dict__.get

        # Any valid search argument is good
        if any(oget(o) for o in search_opts):
            search_builder(opts)
        else:
            parser.print_help()
            parser.error("-s needs at least one other option, excluding -l.")

    return opts, args


def search_builder(opts):  # noqa: PLR0912, PLR0915
    """Builds a list comprehension from the options passed at command-line and
    then evaluates it to return a list of matching device names.
    """
    NetDevices(production_only=opts.nonprod)

    query = "[x for x in nd.all()"

    # Prep variables
    vars = list()
    # print opts

    # For all search arguments, when an explicit match would not be confusing
    # or return inconsistent results, the argument is being upper-cased
    # and a membership (in) test is being performed.
    #
    # For explicit matches, use an equality (==) test instead.

    # nodeName (hostname)  # noqa: ERA001
    if opts.nodename:
        vars.append(f" '{opts.nodename.lower()}' in x.nodeName.lower()")

    # deviceType
    if opts.type:
        vars.append(f" '{opts.type.upper()}' in x.deviceType")

    # onCallName (oncall team)
    if opts.oncall_team:
        vars.append(f" '{opts.oncall_team.lower()}' in x.onCallName.lower()")

    # owningTeam (owning_team)  # noqa: ERA001
    if opts.owning_team:
        vars.append(f" '{opts.owning_team.lower()}' in x.owningTeam.lower()")

    # owner (owning org)
    if opts.owning_org:
        vars.append(f" '{opts.owning_org.upper()}' in x.owner")

    # budgetCode (budget code)
    if opts.budget_code:
        vars.append(f" '{opts.budget_code}' in x.budgetCode")

    # budgetName (budget name)
    if opts.budget_name:
        vars.append(f" '{opts.budget_name.lower()}' in x.budgetName.lower()")

    # vendor
    if opts.vendor:
        vars.append(f" '{opts.vendor.lower()}' in x.vendor")

    # manufacturer
    if opts.manufacturer:
        vars.append(f" '{opts.manufacturer.upper()}' in x.manufacturer")

    # site
    if opts.location:
        vars.append(f" '{opts.location.upper()}' in x.site")

    # make
    if opts.make:
        vars.append(f" '{opts.make.upper()}' in x.make")

    # model
    if opts.model:
        vars.append(f" '{opts.model.upper()}' in x.model")

    # coordinate/rack
    if opts.coordinate:
        vars.append(f" '{opts.coordinate.upper()}' in x.coordinate")

    # Build a list comprehension based on the vars list.
    # so:
    #    [" 'SWITCH' in x.deviceType", 'juniper' in x.vendor"]
    # becomes:
    #   [x for x in nd.all() if 'SWITCH' in x.deviceType and 'juniper' in
    #   x.vendor]
    query += " if"
    vlen = len(vars)
    counter = 1
    for i in range(vlen):
        query += vars[i]
        if counter != vlen:
            query += " and"
        counter += 1

    # Finalize query
    query += "]"
    # print query

    try:
        devlist = eval(query)  # noqa: S307 - dynamic query construction from CLI args
    except TypeError:
        from trigger.conf import settings

        print(
            f"A required field in {settings.NETDEVICES_SOURCE} is missing or invalid.  Please fix the data and try again.",
        )
        sys.exit(1)

    devlist.sort()

    # Store opts_dict for print_results
    opts_dict = vars(opts)

    # Print acls
    if opts.acls:
        acls = set()
        for dev in devlist:
            for acl in dev.acls:
                acls.add(acl)

        dump = [x for x in acls]
        dump.sort()
        for acl in dump:
            print(acl)
    # Print devices
    elif devlist:
        for dev in devlist:
            print(dev)
    else:
        squery = []
        for key, value in opts_dict.items():
            if key not in ("search", "nonprod") and value:
                squery.append(key + "=" + value)
        print("No matches for the query {}.".format(" and ".join(squery)))


def main():
    """Main entry point for the CLI tool."""
    _opts, _args = parse_args(sys.argv)


if __name__ == "__main__":
    main()
