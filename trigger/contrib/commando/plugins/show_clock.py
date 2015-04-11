
import datetime
from twisted.python import log
from trigger.utils import xmltodict, strip_juniper_namespace
from trigger.contrib.commando import CommandoApplication
import xml.etree.ElementTree as ET
from xml.etree.cElementTree import ElementTree, Element, SubElement

task_name = 'show_clock'

def xmlrpc_show_clock(*args, **kwargs):
    """Run 'show clock' on the specified list of `devices`"""
    log.msg('Creating ShowClock')
    sc = ShowClock(*args, **kwargs)
    d = sc.run()
    return d

class ShowClock(CommandoApplication):
    def to_cisco(self, dev, commands=None, extra=None):
        return ['show clock']
    to_brocade = to_cisco

    def to_arista(self, dev, commands=None, extra=None):
        return ['show clock','show uptime']

    def to_juniper(self, dev, commands=None, extra=None):
        """Generates an etree.Element object suitable for use with JunoScript"""
        cmd = Element('get-system-uptime-information')
        self.commands = [cmd]
        return self.commands

    def from_cisco(self, data, device, commands=None):
        """Parse Cisco time"""
        # => '16:18:21.763 GMT Thu Jun 28 2012\n'
        fmt = '%H:%M:%S.%f %Z %a %b %d %Y\n'
        ## Need to structure this into a common json structure
        ## {"current-time":""}
        results = []
        for res in data:
            r = self._parse_datetime(res, fmt)
            jdata = {"current-time":r}
            results.append(jdata)
        self.store_results(device, results)

    def from_brocade(self, data, device, commands=None):
        """
        Parse Brocade time. Brocade switches and routers behave
        differently...
        """
        if device.is_router():
            # => '16:42:04 GMT+00 Thu Jun 28 2012\r\n'
            fmt = '%H:%M:%S GMT+00 %a %b %d %Y\r\n'
        elif device.is_switch():
            # => 'rbridge-id 1: 2012-06-28 16:42:04 Etc/GMT+0\n'
            data = [res.split(': ', 1)[-1] for res in data]
            fmt = '%Y-%m-%d %H:%M:%S Etc/GMT+0\n'
        ## Need to structure this into a common json structure
        ## {"current-time":""}
        results=[]
        for res in data:
            r = self._parse_datetime(res, fmt)
            jdata = {"current-time":r}
            results.append(jdata)
        self.store_results(device, results)

    def from_juniper(self, data, device, commands=None):
        """Do all the magic to parse Junos interfaces"""
        self.raw = data
        results=[]
        for xml in data:
            jdata = xmltodict.parse(
                ET.tostring(xml),
                postprocessor=strip_juniper_namespace,
                xml_attribs=False
            )
            # xml needs to die a quick, but painful death
            sysupinfo = None
            if 'system-uptime-information' in jdata['rpc-reply']:
                sysupinfo = jdata['rpc-reply']['system-uptime-information']
            elif 'multi-routing-engine-results' in jdata['rpc-reply']:
                try:
                    sysupinfo = jdata['rpc-reply']['multi-routing-engine-results']['multi-routing-engine-item']['system-uptime-information']
                except:
                    pass
            if sysupinfo == None:
                currtime = 'Unable to parse'
                ## need to turn this into an error
            else:
                currtime = sysupinfo['current-time']['date-time']
            # => '2013-02-20 21:41:40 UTC'
            fmt = '%Y-%m-%d %H:%M:%S %Z'
            r = self._parse_datetime(currtime, fmt)
            jdata = {'current-time':r}
            #self.data.append({'device':device,'data':jdata})
            results.append(jdata)
        self.store_results(device, results)
        ## UGH
        ## Some devices start with '{"system-uptime-information":{} }'
        ## Some devices start with '{"multi-routing-engine-results": {"multi-routing-engine-item": {"system-uptime-information":{} }}}'

    ##
    ##  This method should move to trigger.utils or elsewhere
    ##
    def _parse_datetime(self, datestr, fmt):
        """
        Given a date string and a format, try to parse and return
        datetime.datetime object.
        """
        try:
            d = datetime.datetime.strptime(datestr, fmt)
            dstr = d.isoformat()
            return dstr
        except ValueError:
            return datestr

