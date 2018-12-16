From SimpleParse documentation: (read the whole thing, but pay special
attention to the last 5 lines)

**DispatchProcessor**

SimpleParse 2.0 provides a simple mechanism for processing result trees,
a recursive series of calls to attributes of a “Processor” object with
functions to automate the call-by-name dispatching.  This processor
implementation is available for examination in the
simpleparse.dispatchprocessor module.  The main functions are:

def dispatch( source, tag, buffer ):\
        """Dispatch on source for tag with buffer\
\
        Find the attribute or key "tag-object" (tag[0]) of source,\
        then call it with (tag, buffer)\
        """\
def dispatchList( source, taglist, buffer ):\
        """Dispatch on source for each tag in taglist with buffer"""\
\
def multiMap( taglist, source=None, buffer=None ):\
        """Convert a taglist to a mapping from
tag-object:[list-of-tags]\
       \
        For instance, if you have items of 3 different types, in any
order,\
        you can retrieve them all sorted by type with multimap(
childlist)\
        then access them by tagobject key.\
\
        If source and buffer are specified, call dispatch on all items.\
        """\
\
def singleMap( taglist, source=None, buffer=None ):\
        """Convert a taglist to a mapping from tag-object:tag,\
        overwritting early with late tags.  If source and buffer\
        are specified, call dispatch on all items."""\
\
def getString( (tag, left, right, sublist), buffer):\
        """Return the string value of the tag passed"""\
\
def lines( start=None, end=None, buffer=None ):\
        """Return number of lines in buffer[start:end]"""

With a class **DispatchProcessor**, which provides a \_\_call\_\_
implementation to trigger dispatching for both "called as root
processor" and "called to process an individual result element" cases.

You define a DispatchProcessor sub-class with methods named for each
production that will be processed by the processor, with signatures of:

from simpleparse.dispatchprocessor import \*\
class MyProcessorClass( DispatchProcessor ):\
        def production\_name( self, (tag,start,stop,subtags), buffer ):\
               """Process the given production and it's children"""

Within those production-handling methods, you can call the dispatch
functions to process the sub-tags of the current production (keep in
mind that the sub-tags "list" may be a None object).  You can see
examples of this processing methodology in
simpleparse.simpleparsegrammar, simpleparse.common.iso\_date and
simpleparse.common.strings (among others).

**For real-world Parsers, where you normally use the same processing
class for all runs of the parser, you can define a default Processor
class like so:**

**class MyParser( Parser ):\
      def buildProcessor( self ):\
           return MyProcessorClass()**

**so that if no processor is explicitly specified in the parse call,
your "MyProcessorClass" instance will be used for processing the
results.**
