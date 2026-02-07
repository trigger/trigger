#!/usr/bin/env python

"""optimizer - ACL Optimizer.

Optimizes filters (usually best on Juniper filters) using
various algorithms to determine which filters can be merged
and removed.
"""

__version__ = "1.5"

import copy
import logging
import signal
import sys
import time
from optparse import OptionParser
from pathlib import Path

from simpleparse.error import ParserSyntaxError

from trigger.acl.parser import ACL, TIP, Comment, parse

stop_all = False

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
)
log = logging.getLogger(__name__)


def sig_handler(s, d):
    global stop_all  # noqa: PLW0603
    stop_all = True


def parse_args(argv):
    parser = OptionParser(
        usage="%prog [options] [acls]",
        description="""ACL Optimizer

Optimizes filters (usually best on Juniper filters) using
various algorithms to determine which filters can be merged
and removed.

There are several phases of optimization which include source
address optimization, destination address optimization, and
destination port optimization.

By default the optimizer will continue to optimize until the
no more optimizations can be made.

This can be very time consuming if run on a very large acl.
It is suggested that the focus argument should be used if
such an acl is needed to be optimized.

This will output to a file: <original_acl_filename>.optimized
    """,
    )

    parser.add_option(
        "-p",
        "--passes",
        type="int",
        default=0,
        help="""The number of passes the optimizer should make.

By defaut the optimizer will continue to make more passes until
no more optimizations can be made. Specify this to limit this.
    """,
    )
    parser.add_option(
        "-f",
        "--focus",
        type="int",
        default=0,
        help="""Focus on a specific set of terms based on the
number of destination ports found. This will count the number
of destination ports, and if the port count is over X, the terms
in which this port was found will be accounted for in its optimization
checks. All other terms will be left alone. By default this feature
is set to 0 (or off).
        """,
    )

    parser.add_option(
        "",
        "--no-source-ip",
        action="store_true",
        help="This will turn off the source-ip optimization",
    )
    parser.add_option(
        "",
        "--no-destination-ip",
        action="store_true",
        help="This will turn off the destination-ip optimization",
    )
    parser.add_option(
        "",
        "--no-destination-port",
        action="store_true",
        help="This will turn off the destination-port optimization",
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        help="Turn on verbose/debug output",
    )
    parser.add_option(
        "",
        "--no-expires",
        action="store_true",
        help="If a term includes an expire date, mark non-eligible for optimize",
    )

    parser.add_option(
        "-d",
        "--debug",
        action="store_true",
        help="Warning: this is very noisy. It will display every action"
        "from the optimization process.",
    )

    opts, args = parser.parse_args(argv)

    return opts, args


class ProgressMeter:
    """Display progress during ACL optimization."""

    def __init__(self, **kw):
        # What time do we start tracking our progress from?
        self.timestamp = kw.get("timestamp", time.time())
        # What kind of unit are we tracking?
        self.unit = str(kw.get("unit", ""))
        # Number of units to process
        self.total = int(kw.get("total", 100))
        # Number of units already processed
        self.count = int(kw.get("count", 0))
        # Refresh rate in seconds
        self.rate_refresh = float(kw.get("rate_refresh", 0.5))
        # Number of ticks in meter
        self.meter_ticks = int(kw.get("ticks", 60))
        self.meter_division = float(self.total) / self.meter_ticks
        self.meter_value = int(self.count / self.meter_division)
        self.last_update = None
        self.rate_history_idx = 0
        self.rate_history_len = 10
        self.rate_history = [None] * self.rate_history_len
        self.rate_current = 0.0
        self.last_refresh = 0
        self.prev_meter_len = 0

    def update(self, count, **kw):
        now = time.time()
        # Caclulate rate of progress
        rate = 0.0
        # Add count to Total
        self.count += count
        self.count = min(self.count, self.total)
        if self.last_update:
            delta = now - float(self.last_update)
            rate = count / delta if delta else count
            self.rate_history[self.rate_history_idx] = rate
            self.rate_history_idx += 1
            self.rate_history_idx %= self.rate_history_len
            cnt = 0
            total = 0.0
            # Average rate history
            for rate in self.rate_history:
                if rate is None:
                    continue
                cnt += 1
                total += rate
            rate = total / cnt
        self.rate_current = rate
        self.last_update = now
        # Device Total by meter division
        value = int(self.count / self.meter_division)
        self.meter_value = max(self.meter_value, value)
        if self.last_refresh:
            if (now - self.last_refresh) > self.rate_refresh or (
                self.count >= self.total
            ):
                self.refresh()
        else:
            self.refresh()

    def get_meter(self, **kw):
        bar = "-" * self.meter_value
        pad = " " * (self.meter_ticks - self.meter_value)
        perc = (float(self.count) / self.total) * 100
        return "[%s>%s] %d%%  %.1f/sec" % (bar, pad, perc, self.rate_current)

    def refresh(self, **kw):
        # Clear line and return cursor to start-of-line
        sys.stderr.write(" " * self.prev_meter_len + "\x08" * self.prev_meter_len)
        # Get meter text
        meter_text = self.get_meter(**kw)
        # Write meter and return cursor to start-of-line
        sys.stderr.write(meter_text + "\x08" * len(meter_text))
        self.prev_meter_len = len(meter_text)

        # Are we finished?
        if self.count >= self.total:
            sys.stderr.write("\n")
        sys.stderr.flush()
        # Timestamp
        self.last_refresh = time.time()


def focus_terms(pcount, terms):  # noqa: PLR0912
    """Generates a list of term names that have a port count
    greater than pcount for the optimizer to 'focus' in on.
    """
    focused = dict()
    matched_ports = dict()
    ports = dict()

    for term in terms:
        if "source-port" in term.match:
            continue

        if "destination-port" not in term.match:
            continue

        for port in term.match["destination-port"]:
            if port == 0:
                continue

            if port in ports:
                ports[port] += 1
            else:
                ports[port] = 1

    for port, cnt in ports.items():
        if cnt >= pcount:
            log.info("port %s had a count of %d" % (str(port), cnt))
            matched_ports[port] = 1

    for term in terms:
        if "destination-port" not in term.match:
            continue
        if "source-port" in term.match:
            continue

        for tport in term.match["destination-port"]:
            if tport in matched_ports:
                focused[term.name] = 1
                break

    log.info("%d focused terms" % len(focused))
    return focused


chk_keys = ["protocol", "source-address", "destination-address", "destination-port"]

rej_keys = ["reject", "deny", "discard"]


def optimize_terms(terms, focused, which, opts):  # noqa: PLR0912, PLR0915
    global stop_all  # noqa: PLW0602
    to_delete = dict()
    other = ""
    total = 0

    total = len(terms)

    if which == "source-address":
        other = ["destination-address"]
    elif which == "destination-address":
        other = ["source-address"]
    else:
        # this is used primarily for port optimization
        other = ["source-address", "destination-address"]

    meter = ProgressMeter(total=total)

    for term1 in terms:
        if stop_all:
            break

        meter.update(1)

        if focused and term1.name not in focused:
            continue

        dont_merge = False
        if opts.no_expires:
            for c in term1.comments:
                if "UNTIL" in c and "Never" not in c:
                    dont_merge = True

        if dont_merge:
            continue

        # make sure that there are not any source-ports
        # defined in term1
        if (
            "destination-port" not in term1.match
            or "source-port" in term1.match
            or term1.action[0] in rej_keys
            or term1 in to_delete
        ):
            continue

        for term2 in terms:
            breaker = False

            if stop_all:
                break

            log.debug(
                "Comparing term %s to term %s [%d terms deleted]"
                % (term1.name, term2.name, len(to_delete)),
            )
            if focused and term2.name not in focused:
                continue

                if opts.no_expires:
                    for c in term2.comments:
                        if "UNTIL" in c and "Never" not in c:
                            dont_merge = True

                if dont_merge:
                    continue

            # check to make sure that neither term
            # has been marked for deletion. Also
            # check to make sure we're not comparing
            # the same terms, and this is not a
            # rejected action.
            if (
                term1.name in to_delete
                or term2.name in to_delete
                or term1.name == term2.name
                or term2.action[0] in rej_keys
                or "source-port" in term2.match
            ):
                continue

            # check to make sure both terms include somethin
            # that can be matched.
            for key in chk_keys:
                if key not in term1.match or key not in term2.match:
                    breaker = True
                    break

            if breaker:
                continue

            # make sure that both protocols match up.
            if len(term1.match["protocol"]) != len(term2.match["protocol"]):
                continue

            if "icmp" in term1.match["protocol"] or "icmp" in term2.match["protocol"]:
                break

            for proto in term1.match["protocol"]:
                if proto not in term2.match["protocol"]:
                    breaker = True
                    break

            if breaker:
                continue

            # we don't do this check if we are optimizing destination-ports
            if which != "destination-port":
                # make sure that both destination-ports match up.
                if len(term1.match["destination-port"]) != len(
                    term2.match["destination-port"],
                ):
                    breaker = True
                    continue

                for port in term1.match["destination-port"]:
                    for port2 in term2.match["destination-port"]:
                        if port != port2:
                            breaker = True
                        if breaker:
                            break
                    if breaker:
                        break

                if breaker:
                    continue

            for ent in other:
                # check to make sure that the other side
                # has the IP's from term1 to term2
                len1 = len(term1.match[ent])
                len2 = len(term2.match[ent])

                if len1 != len2:
                    breaker = True
                    break

                matches = [x for x in term1.match[ent] if x in term2.match[ent]]

                if len(matches) != len1:
                    breaker = True
                    break
                matches = [x for x in term2.match[ent] if x in term1.match[ent]]

                if len(matches) != len2:
                    breaker = True
                    break

            if breaker:
                continue

            # append old comments
            for comment in term1.comments:
                term2.comments.append(comment)

            ips = []
            for to_add in term1.match[which]:
                term2.match[which].append(to_add)
                ips.append(str(to_add))

            cmt = Comment(
                "merged [({}) {}] from {}".format(which, ",".join(ips), term1.name),
            )

            term2.comments.append(cmt)

            to_delete[term1.name] = 1

    return [term for term in terms if term.name not in to_delete]


def terms_unchunk(chunks):
    terms = []

    for chunk in chunks:
        terms.extend(chunk)

    return terms


def terms_chunker(terms):
    """Break filter into chunks that are the aggregate of the same modifier.

    What this means is if we have the following term structure:

    term1 { accept }
    term2 { accept }
    term3 { accept }
    term4 { deny }
    term5 { deny }
    term6 { accept }
    term7 { accept }
    term8 { deny }

    We would break it up as so:

    chunks = [ [term1, term2, term3], [term4, term5], [term6, term7, term8] ]

    We then only optimize on chunks of terms so that we don't accidently
    optimize something accepted above a deny to an accept below the deny.
    """
    ret = []
    current_chunk = []

    total = len(terms)
    meter = ProgressMeter(total=total)
    current_modifier = None

    for term in terms:
        meter.update(1)
        if current_modifier is None:
            current_modifier = term.action[0]
        if current_modifier != term.action[0]:
            ret.append(copy.copy(current_chunk))
            current_chunk = []
            current_modifier = term.action[0]

        current_chunk.append(term)

    ret.append(copy.copy(current_chunk))

    return ret


def optimize(opts, terms, focused):
    global stop_all  # noqa: PLW0602

    terms_old = terms
    mtypes = []

    if not opts.no_source_ip:
        mtypes.append("source-address")
    if not opts.no_destination_ip:
        mtypes.append("destination-address")
    if not opts.no_destination_port:
        mtypes.append("destination-port")

    for term in terms:
        for mtype in mtypes:
            if mtype == "destination-port":
                continue
            if mtype not in term.match:
                term.match[mtype] = [TIP("0.0.0.0/0")]

    chunks = terms_chunker(terms)

    for type in mtypes:
        if stop_all:
            return terms

        for chunk_count, chunk in enumerate(chunks):
            log.info("Optimizing %s [Chunk %d]" % (type, chunk_count))
            chunks[chunk_count] = optimize_terms(chunk, focused, type, opts)
            log.info("TCount: %d/%d" % (len(terms_old), len(terms)))

    return terms_unchunk(chunks)


def do_work(opts, files):  # noqa: PLR0912, PLR0915
    global stop_all  # noqa: PLW0602
    for acl_file in files:
        focused = None
        out_file = acl_file + ".optimized"

        if stop_all:
            return

        log.info(f"Parsing {acl_file}")

        try:
            with Path(acl_file).open() as fh:
                acl = parse(fh)
        except ParserSyntaxError as e:
            etxt = str(e).split()
            log.error(etxt)
            return

        log.info("Done parsing")

        len(acl.terms)

        if opts.focus:
            log.info("Finding focused terms")
            focused = focus_terms(opts.focus, acl.terms)
            if not focused:
                log.warn(f"No focused terms could be found in acl {acl_file}")
                continue

            log.info("Done focused term")

        passes = 1

        terms_old = acl.terms

        # destination ports should always be optimized LAST
        real_port_optimize_opt = opts.no_destination_port
        # first set to none
        opts.no_destination_port = True

        while True:
            if stop_all:
                break

            log.info("Optimization pass %d" % passes)
            terms = optimize(opts, terms_old, focused)

            if opts.passes and passes >= opts.passes:
                break

            if len(terms_old) == len(terms):
                break

            terms_old = terms
            passes += 1

        terms_old = terms
        if not real_port_optimize_opt:
            passes = 1
            opts.no_destination_port = False
            opts.no_source_ip = True
            opts.no_destination_ip = True
            while True:
                if stop_all:
                    break

                log.info("PORT Optimization pass %d" % passes)
                terms = optimize(opts, terms_old, focused)

                if opts.passes and passes >= opts.passes:
                    break

                if len(terms_old) == len(terms):
                    break

                terms_old = terms
                passes += 1

        new_acl = ACL()
        new_acl.policers = acl.policers
        new_acl.format = acl.format
        new_acl.comments = acl.comments
        new_acl.name = acl.name
        new_acl.terms = terms

        with Path(out_file).open("w") as out:
            for x in new_acl.output(replace=True):
                print(x, file=out)


def main():
    """Main entry point for the CLI tool."""
    opts, args = parse_args(sys.argv)
    if opts.debug:
        log.setLevel(logging.DEBUG)

    acl_files = args[1:]

    signal.signal(signal.SIGINT, sig_handler)

    do_work(opts, acl_files)


if __name__ == "__main__":
    main()
