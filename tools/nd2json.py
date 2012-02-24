#!/usr/bin/env python

# nd2json.py - Converts netdevices.xml to netdevices.json and reports
# performance stuff

from xml.etree.cElementTree import ElementTree, parse
try:
    import simplejson as json
except ImportError:
    import json
import sys
import time


if len(sys.argv) < 2:
    sys.exit("usage: %s </path/to/netdevices.xml>" % sys.argv[0])
else:
    ndfile = sys.argv[1]

print # Parse XML
print 'Parsing XML', ndfile
start = time.time()
nodes = parse(ndfile).findall('device')
print 'Done:', time.time() - start, 'seconds.'
devices = []

print # Convert to Python structure

print 'Converting to Python structure.'
start = time.time()
for node in nodes:
    dev = {}
    for e in node.getchildren():
        dev[e.tag] = e.text
    devices.append(dev)
print 'Done:', time.time() - start, 'seconds.'

print # Convert to JSON

'''
print 'Dumping to JSON...'
start = time.time()
jsondata = json.dumps(devices)
print 'Done:', time.time() - start, 'seconds.'
'''

print # Writing to file

outfile = 'netdevices.json'
with open(outfile, 'wb') as f:
    print 'Writing to disk...'
    start = time.time()
    json.dump(devices, f, ensure_ascii=False, check_circular=False, indent=4)
    #json.dump(devices, f, ensure_ascii=False, check_circular=False)
    #f.write(jsondata)
    print 'Done:', time.time() - start, 'seconds.'
    #print 'Wrote {0} bytes to {1}'.format(len(jsondata), outfile)

print # Reading from file

with open(outfile, 'rb') as g:
    print 'Reading from disk...'
    start = time.time()
    jsondata = json.load(g)
    print 'Done:', time.time() - start, 'seconds.'
