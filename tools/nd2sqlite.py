#!/usr/bin/env python

# nd2sqlite.py - Converts netdevices.xml into a SQLite database and also prints
# some performance stuff

from xml.etree.cElementTree import ElementTree, parse
try:
    import simplejson as json
except ImportError:
    import json
import time
import sys
import sqlite3 as sqlite

if len(sys.argv) < 3:
    sys.exit("usage: %s </path/to/netdevices.xml> </path/to/sqlite-db-file>" % sys.argv[0])
else:
    ndfile = sys.argv[1]
    sqlitefile = sys.argv[2]

print # Parse XML
print 'Parsing XML', ndfile
start = time.time()
nodes = parse(ndfile).findall('device')
print 'Done:', time.time() - start, 'seconds.'
#devices = []

connection = sqlite.connect(sqlitefile)
cursor = connection.cursor()

print # Convert to Python structure

print 'Inserting into sqlite...'
start = time.time()
for node in nodes:
    keys = []
    vals = []
    for e in node.getchildren():
        keys.append(e.tag)
        vals.append(e.text)
    keystr = ', '.join(keys)
    valstr = ','.join('?' * len(vals))
    #sql = ''' INSERT INTO netdevices ( {0}) VALUES ( {1}); '''.format(keystr, valstr)
    sql = '''INSERT INTO netdevices ( {0} ) VALUES ( {1} )'''.format(keystr, valstr)
    cursor.execute(sql, vals)

connection.commit()

"""
colfetch  = cursor.execute('pragma table_info(netdevices)')
results = colfetch.fetchall()
columns = [r[1] for r in results]
devfetch = cursor.execute('select * from netdevices')
devrows = devfetch.fetchall()

for row in devrows:
    data = zip(columns, row)
    print data
"""

cursor.close()
connection.close()
print 'Done:', time.time() - start, 'seconds.'
