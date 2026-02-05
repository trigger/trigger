# a test for except processing
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / ".."))
from trigger import acl

PARSIT = """
filter fire1 {
    term 1 {
        from {
            source-address {
                192.168.5.0/24 except;
                192.168.6.0/24;
            }
        }
        then {
            count reject-pref1-1;
            log;
            reject;
        }
    }
    term 2 {
        then {
            count reject-pref1-2;
            log;
            accept;
        }
    }
}
"""
y = acl.parse(PARSIT)
print(y.terms[0].match)
print("\n".join(acl.parse(PARSIT).output_junos()))
# following should fail
