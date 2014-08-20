# SRX Parsing Notes / Log #

## Questions ##
 * Question: do we need to add "replace:" statements to this grammar (see the
   junos.py grammar in trigger)? When are these statements needed to be parsed? 

## Links ##
 * [Simple Parse Notation](http://simpleparse.sourceforge.net/simpleparse_grammars.html)
    * Simple Parse is the library that Trigger uses for ACL/firewall config parsing.
     pyparsing is used for other things (ask Jathan for details, the library is
     poorly documented)
 * [Syntax Tree Generator](http://mshang.ca/syntree/)
    * A very basic automagical syntax tree diagram creator. See the **Big Picture SRX
       Syntax Tree** section below for details.

## The Approach ##
At first I tried to morph the trigger/trigger/acl/junos.py file into the new SRX
parsing information. However, there are major syntactical differences that
quickly made that a non-option (1). I went back to the notes I took from our
second meeting with Jathan, and found that the approach he thought we should
take was to morph the trigger/trigger/NetScreen.py file into the new SRX parser.
This makes a lot more sense because the NetScreen parser seems to already have
some stateful support built-in, and it already supports the overall syntax of
the SRX firewall configs (namely the policies/zones/applications) (2).
Unfortunately, this NetScreen-centric approach makes the recent parser.py
refactoring a little redundant, since all parsing will be done in our new SRX
file (tentatively trigger/trigger/juniper_srx.py).

Structural elements and grammar styles will be copied from the junos.py into
juniper_srx.py as needed. NetScreen-specific code (like grammar definitions)
will be stripped.

 (1): Junos configs don't have any concept of applications or zones. The
 latter wouldn't be that hard to work around (mostly since Diana says we don't
 need to manage SRX zones with trigger), but the applications are essential.
 Furthermore, the Junos configs have a firewall > family > filter > term
 hierarchy, and the SRX has a very different heirarchy (security > policies >
 from-zone ___ to-zone ___ > policy num) with additional sections outside of the
 basic configs (zones and applications). 

 (2): NetScreen configs, while structurally very different, have the same
 high-level concepts as the SRX configs. A major difference though is that
 NetScreen has a "top-level" address book that associates IP objects with names.
 In SRX, each zone has its own address-book specifying these associations.

### SRX Grammar Documentation / Exploration ###
I've had quite some time to familiarize myself with the old junos.py stuff. It's
helped to point me in the right direction as far as actually making the SRX
grammar goes. I'll begin with a loose top-to-bottom specification of the needed SRX
grammar. 

#### Loose Grammar Definition ####
Note: some of the whitespace indicators will be replaced with jws (and others) in
final grammar (jws includes Junos comments and other valid symbols).    

Note: final grammar will include "replace:" statements. These indicate sections to
add/replace when you load the config onto the device.

Note: EBNF symbols used roughly correspond to those used by the simple parse library.
In some places where astrisks are used, plus signs may need to be used (I'm still
figuring this out, obviously).  

    security        :=  "security", ws, "{", ws, policies, ws, "}"
    policies        :=  "policies", ws, "{", ws, (from_zone)*, "}"
    from_zone       :=  "from-zone", ws, zone_name, ws, "to-zone", ws, zone_name, ws,
                            "{", ws, (policy)*, ws, "}"
    zone_name       :=  valid characters for zone names
    policy          :=  "policy", ws, policy_name, ws, "{", ws, match, then, "}"
    policy_name     :=  valid characters for policy names
    match           :=  "match", ws, "{", match_contents, ws, "}"
    then            :=  "then", ws, "{", then_contents, ws, "}"
    match_contents  :=  all valid match lines (each terminated by semi colons)
                            Note: this also can be braced sections, which aren't
                            terminated by semi colons.
    then_contents   :=  all valid then lines (each terminated by semi colons)
                            Note: this also can be braced sections, which aren't
                            terminated by semi colons.
    zones           :=  "zones", ws, "{", (security_zone)*, ws, "}"
    security_zone   :=  "security-zone", ws, zone_name, ws, "{", sec_zone_cntnts, ws,
                            "}"
    sec_zone_cntnts :=  address_book, interfaces, all other required sections
                            Note: these are in no particular order, which I don't
                            know how to specify in EBNF nor the simple parse library
                            notation)
    address_book    :=  "address-book", ws, "{", ws, ( ("address", ws,
                            ip_address_range_object, semicolon) / (address_set) )+,
                            ws, "}"
                            Note: I don't know if more things can go inside of an
                            address book...
    address_set     := "address-set", ws, addr_set_name, ws, "{", addr_set_cntnts,
                            ws, "}"
    addr_set_name   := any valid characters for address set names
    addr_set_cntnts := ("address", ws, ip_address_object, semicolon)+

## Progress ##
This section will be more of a log format, with more recent progress updates
towards the top.

### 2014-08-20 ###
Joseph's last day is tomorrow. He has been making sure that all the current code is pushed 
to the repos and that the informational documents are uploaded as well. The current state of
the srx_grammar is that it needs work. **There is the basic grammar and basic object implementation.
These need to be flushed out. juniper_srx.py contains the work done.**

### 2014-08-18 ###
Joseph spent the past week editing the the bulk IP adder for SSG and SRX devices.  

### 2014-08-11 ###
Joseph has implemented a basic grammar to parse the SRX ACL. After being parsed, the ACL is
put into objects. He has implemented several of these objects.

### 2014-08-07 ###
Joseph has made major progress in implementing the SRX parser. He also filed a
pull request with the main project for the refactoring he did earlier.

### 2014-08-05 ###
The past several workdays have been spent working on a series of band-aid
python programs that automate adding large numbers of IP addresses into
Juniper SSG and SRX firewalls. Work on the SRX parser has resumed as of
today.

### 2014-07-24 ###
Realized that I do not have a rigourous specification of Juniper SRX grammar. Will
begin documenting the relevant configurations. Sidenote: I really wish I had a
whiteboard right now...

### 2014-07-22 ###
Initially started to modify the junos.py file to suit SRX needs. It became
apparent that this was not going to work out. Changed to modifying the
NetScreen.py file. 

## Big Picture SRX Syntax Tree ##
See http://mshang.ca/syntree/ for a neat syntax tree generator. Paste the
following into the generator to get a nice SRX security syntax tree:

    [security [policies [<from/to> [<policies> [match][then]]]] [zones [<security-zone>[address-book ][interfaces]]]]

sections wrapped in angle brackets are repeatable. Not everything we need to
support is displayed; the diagram only shows the "big picture".

We may also need to suppor the applications section (which isn't under security):

    [applications [<application>[protocol][source-port][destination-port]]]


