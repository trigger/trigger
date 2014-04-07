"""
fe_extensions.py - Contains parser extensions for the 'fe' utility
"""
from trigger import acl
import IPy
from simpleparse.parser import Parser
import trigger.exceptions

declaration = r'''
root := 'policy-options',! "problem parsing policy options",ws,'{',ws,plb,ws,'}',ws
<ws> := [ \t\n]*
replace := 'replace:'
identifier := [-a-zA-Z]+
plb := replace?,ws,'prefix-list',ws,identifier,ws,'{',ples,ws,'}'
ples := ple+
ple := ws,?-"}",! "problem around line %(line)s",ip,ws,';'
ip := [0-9]+,'.',[0-9]+,'.',[0-9]+,'.',[0-9]+,('/',[0-9]+)?
'''

from simpleparse.dispatchprocessor import *
class MyProcessorClass( DispatchProcessor ):
    # example
    def production_name( self, (tag,start,stop,subtags), buffer ):
        """Process the given production and its children"""
        pass

    def plb( self, (tag,start,stop,subtags), buffer):
        return [dispatchList(self,subtags,buffer)]
        pass

    def identifier( self, (tag,start,stop,subtags),buffer):
        return buffer[start:stop]

    def ip( self, (tag,start,stop,subtags), buffer):
        try:
            return IPy.IP(buffer[start:stop])
        except ValueError as ve:
            e = trigger.exceptions.ParseError("Can't parse this as an IP address: %s "
                                              "(around line %d)" %
                                              (buffer[start:stop], lines(0,start,buffer)))
            raise e

    def replace( self, (tag,start,stop,subtags), buffer):
        return 'replace'

    def ples( self, (tag,start,stop,subtags), buffer):
        return ['ples',dispatchList(self,subtags,buffer)]

    def ple( self, (tag,start,stop,subtags), buffer):
        return dispatch(self,subtags[0],buffer)

class MyParser(Parser):
    def buildProcessor( self ):
        return MyProcessorClass()

def parse_prefixlist(filename):
    import pdb; pdb.set_trace()
    fc = open(filename).read()
    # add quick test here... like a regular expression test
    parser = MyParser(declaration)
    x = parser.parse(fc)
    if x[-1] == len(fc):
        # success, we 'ate' the whole file
        return True, fc
    return False, None
