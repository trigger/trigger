#!/usr/bin/env python

"""gnng - Fetches network devices interfaces and displays them in a table view.

Fetches interface information from routing and firewall devices. This includes
network and IP information along with the inbound and outbound filters that
may be applied to the interface. Works on Juniper, Netscreen, Foundry, and Cisco
devices.
"""

import csv
import os
import sys
from collections import namedtuple
from optparse import OptionParser
from pathlib import Path
from sqlite3 import dbapi2 as sqlite

import prettytable

from trigger.cmds import NetACLInfo

# Put this here until the default changes to not load ACLs from redis.
from trigger.conf import settings
from trigger.netdevices import NetDevices, device_match

settings.WITH_ACLS = False

# Constants
DEBUG = os.getenv("DEBUG")
MAX_CONNS = 10
ROW_LABELS = ["Interface", "Addresses", "Subnets", "ACLs IN", "ACLs OUT", "Description"]

# Namedtuples
RowData = namedtuple("RowData", "all_rows subnet_table")
DottyData = namedtuple("DottyData", "graph links")


def parse_args(argv):  # noqa: D103
    parser = OptionParser(
        usage="%prog [options] [routers]",
        description="""GetNets-NG

Fetches interface information from routing and firewall devices. This includes
network and IP information along with the inbound and outbound filters that
may be applied to the interface. Skips un-numbered and disabled interfaces by
default. Works on Cisco, Foundry, Juniper, and NetScreen devices.""",
    )
    parser.add_option("-a", "--all", action="store_true", help="run on all devices")
    parser.add_option(
        "-c",
        "--csv",
        action="store_true",
        help="output the data in CSV format instead.",
    )
    parser.add_option(
        "-d",
        "--include-disabled",
        action="store_true",
        help="include disabled interfaces.",
    )
    parser.add_option(
        "-u",
        "--include-unnumbered",
        action="store_true",
        help="include un-numbered interfaces.",
    )
    parser.add_option(
        "-j",
        "--jobs",
        type="int",
        default=MAX_CONNS,
        help="maximum simultaneous connections to maintain.",
    )
    parser.add_option(
        "-N",
        "--nonprod",
        action="store_false",
        default=True,
        help="Include non-production devices from the query or "
        "[routers].  Requires a legitimate query.",
    )
    parser.add_option("-s", "--sqldb", type="str", help="output to SQLite DB")
    parser.add_option(
        "",
        "--dotty",
        action="store_true",
        help="output connect-to information in dotty format.",
    )
    parser.add_option(
        "",
        "--filter-on-group",
        action="append",
        help="Run on all devices owned by this group",
    )
    parser.add_option(
        "",
        "--filter-on-type",
        action="append",
        help="Run on all devices with this device type",
    )

    opts, args = parser.parse_args(argv)

    if len(args) == 1 and not opts.all and not opts.filter_on_type:
        parser.print_help()
        sys.exit(1)

    return opts, args


def fetch_router_list(args, opts):
    """Turns a list of device names into device objects, skipping unsupported,
    invalid, or filtered devices.
    """  # noqa: D401, D205
    nd = NetDevices(production_only=opts.nonprod)
    ret = []
    blocked_groups = []
    if args:
        for arg in args:
            # Try to find the device, but fail gracefully if it can't be found
            device = device_match(arg)
            if not pass_filters(device, opts) or device is None:
                continue
            ret.append(device)

    else:
        for entry in nd.values():
            if entry.owningTeam in blocked_groups:
                continue
            if not pass_filters(entry, opts):
                continue
            ret.append(entry)

    return sorted(ret, reverse=True)


def pass_filters(device, opts):
    """Used by fetch_router_list() to filter a device based on command-line arguments."""  # noqa: D401
    if opts.filter_on_group and device.owningTeam not in opts.filter_on_group:
        return False
    return not (opts.filter_on_type and device.deviceType not in opts.filter_on_type)


def write_sqldb(sqlfile, dev, rows):
    """Write device fields to sqlite db."""
    create_table = False

    if not Path(sqlfile).is_file():
        create_table = True

    connection = sqlite.connect(sqlfile)
    cursor = connection.cursor()

    if create_table:
        # if the db doesn't exist we want to create the table.
        cursor.execute("""
        CREATE TABLE dev_nets (
            id            INTEGER PRIMARY KEY,
            insert_date   DATE,
            device_name   VARCHAR(128),
            iface_name    VARCHAR(32),
            iface_addrs   VARCHAR(1024),
            iface_subnets VARCHAR(1024),
            iface_inacl   VARCHAR(32),
            iface_outacl  VARCHAR(32),
            iface_descr   VARCHAR(1024)
        );
        """)
        cursor.execute("""
        CREATE TRIGGER auto_date AFTER INSERT ON dev_nets
        BEGIN
            UPDATE dev_nets SET insert_date = DATETIME('NOW')
                WHERE rowid = new.rowid;
        END;
        """)

    for row in rows:
        iface, addrs, snets, inacl, outacl, desc = row
        cursor.execute(
            f"""
            INSERT INTO dev_nets (
                device_name,
                iface_name,
                iface_addrs,
                iface_subnets,
                iface_inacl,
                iface_outacl,
                iface_descr )
            VALUES (
                '{dev}', '{iface}', '{addrs}',
                '{snets}', '{inacl}', '{outacl}', '{desc}'
            );""",  # noqa: S608 - local sqlite, not user input
        )

    connection.commit()
    cursor.close()
    connection.close()


def get_interface_data(devices, production_only=True, max_conns=MAX_CONNS, opts=None):
    """Fetch interface information from ``devices`` and return it as a dict.

    :param devices:
        List of device hostnames

    :param production_only:
        Whether to include only devices marked as "PRODUCTION"

    :param max_conns:
        Max number of simultaneous connections
    """
    skip_disabled = not opts.include_disabled  # Inverse of include is skip :D
    ninfo = NetACLInfo(
        devices=devices,
        production_only=production_only,
        max_conns=max_conns,
        skip_disabled=skip_disabled,
    )
    ninfo.run()
    if DEBUG:
        print("NetACLInfo done!")

    return ninfo.config


def build_output(main_data, opts, labels=None):
    """Iterate the interface data, then build and return row data.

    :param main_data:
        Dictionary of interface data

    :param opts:
        OptionParser object

    :param labels:
        Row labels for table output
    """
    if labels is None:
        labels = ROW_LABELS

    subnet_table = {}
    all_rows = {}

    for dev, data in main_data.items():
        rows = []
        interfaces = sorted(data)
        for interface in interfaces:
            iface = data[interface]

            # Maybe skip down interfaces
            if "addr" not in iface and not opts.include_disabled:
                continue

            if DEBUG:
                print(">>> ", interface)

            addrs = iface["addr"]
            subns = iface["subnets"]
            acls_in = iface["acl_in"]
            acls_out = iface["acl_out"]
            desctext = " ".join(iface.get("description")).replace(" : ", ":")

            # Maybe skip un-numbered interfaces
            if not addrs and not opts.include_unnumbered:
                continue

            # Trim the description
            if not opts.csv:
                desctext = desctext[0:50]

            addresses = []
            subnets = []

            addresses = [a.strNormal() for a in addrs]

            for s in subns:
                subnets.append(s.strNormal())

                if s in subnet_table:
                    subnet_table[s].append((dev, interface, addrs))
                else:
                    subnet_table[s] = [(dev, interface, addrs)]

            if DEBUG:
                print("\t in:", acls_in)
                print("\t ou:", acls_out)
            rows.append(
                [
                    interface,
                    " ".join(addresses),
                    " ".join(subnets),
                    "\n".join(acls_in),
                    "\n".join(acls_out),
                    desctext,
                ],
            )

        all_rows[dev.nodeName] = rows

    return RowData(all_rows, subnet_table)


def handle_output(all_rows, opts):
    """Do stuff with the output data.

    :param all_rows:
        A list of lists of row data

    :param opts:
        OptionParser object
    """
    for dev, rows in all_rows.items():
        if opts.csv:
            writer = csv.writer(sys.stdout)
            for row in rows:
                writer.writerow([dev, *row])
        elif opts.dotty:
            continue
        elif opts.sqldb:
            write_sqldb(opts.sqldb, dev, rows)
        else:
            print(f"DEVICE: {dev}")
            print_table(rows)


def print_table(rows, labels=None):
    """Print the interface table for a device."""
    if labels is None:
        labels = ROW_LABELS

    output_table = prettytable.PrettyTable()
    output_table.field_names = labels
    output_table.align = "l"
    output_table.vrules = prettytable.prettytable.ALL
    output_table.hrules = prettytable.prettytable.HEADER

    for row in rows:
        row = [x.strip() for x in row]  # noqa: PLW2901
        output_table.add_row(row)

    print(output_table)
    print()


def output_dotty(subnet_table, display=True):
    """Output and return dotty config for a ``subnet_table``.

    :param subnet_table:
        Dict mapping subnets to devices and interfaces
    """
    links = {}

    for devs in subnet_table.values():
        if len(devs) > 1:
            router1 = devs[0][0]
            router2 = devs[1][0]

            kf1 = router1 in links
            kf2 = router2 in links

            if kf1:
                if router2 not in links[router1]:
                    links[router1].append(router2)

            elif kf2:
                if router1 not in links[router2]:
                    links[router2].append(router1)

            else:
                links[router1] = [router2]

    if not links:
        print("No valid links for dotty generation.")
        return None

    NetDevices()  # This uses the pre-existing NetDevices singleton

    graph = """graph network {
    overlap=scale; center=true; orientation=land;
    resolution=0.10; rankdir=LR; ratio=fill;
    node [fontname=Courier, fontsize=10]"""

    for leaf, subleaves in links.items():
        for subleaf in subleaves:
            graph += f'"{leaf.shortName}"--"{subleaf.shortName}"\n'
    graph += "\n}"

    if display:
        print(graph)

    return DottyData(graph, links)


def main():
    """Main entry point for the CLI tool."""  # noqa: D401
    opts, args = parse_args(sys.argv)

    if opts.all or opts.filter_on_type:
        routers = fetch_router_list(None, opts)
    else:
        routers = fetch_router_list(args[1:], opts)

    if not routers:
        sys.exit(1)

    main_data = get_interface_data(
        devices=routers,
        production_only=opts.nonprod,
        opts=opts,
    )
    all_rows, subnet_table = build_output(main_data, opts)
    handle_output(all_rows, opts)

    if opts.dotty:
        output_dotty(subnet_table)


if __name__ == "__main__":
    main()
