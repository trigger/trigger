#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Do It (Next Generation)

Uses Trigger framework to run commands or load configs on netdevices

This is the base module called by front-end scripts.

main() is never actually called from within here, and takes a single argument:
  the docommand.do class that needs to be instanced.

This base method exists so that tools using the module can maintain a consistent 
useability wrt arguments and output

Scripts using this module are passed cmdline arguments specifying the device(s) and 
command(s)/configuration line(s) desired to run/load.

The list of devices and configuration lines may be specified either directly on the 
commandline (comma-separated values) or by specifying files containing these lists.
Any files containing configs *must* be located in a tftp directory.
Configs specified on commandline will either be written to a tftp directory in a tmp file (future)
or run directly on the devices (current)

Please see --help for details on how to construct your arguments

(not yet supported)
--device-path arg to specify directory containing configs.  
Each file would be named as the devname and 
contents would be the config you want loaded to that specific device.
**waiting on enhancements to Commando for implementation**

(not yet supported)
--match arg to allow matching on netdevices.xml fields to compile list of devices
**not waiting on anything, just not implemented in v1**

"""
import sys
import re
import os
import sys
from optparse import OptionParser
import docommand.do

PROD_ONLY = False
DEBUG = False
VERBOSE = False
PUSH = False
TIMEOUT = 30

def main(action_class=None):
    """void = main(CommandoClass action_class)"""
    if action_class is None:
        print "You should not have called this directly"
        print "You need to specify Do or Config as an action class"
        sys.exit()

    opts, args = parse_args(sys.argv)
    work = get_jobs(opts)
    results = do_work(work, action_class)
    printResults(results)
    print "enjoy."

def get_jobs(opts):
    """
    list jobs = get_jobs(dict opts)

    Based on which arguments are provided, figure out what is loaded/run on
    which devices and create a list of objects matching the 2::

        job = {'d': [],'c': [],'f': []}

    Is read as "load ALL configs listed in 'c' on ALL devs listed in 'd'". Each
    such grouping is a separate job.

    Future enhancements:
    
    + If multiple jobs exist for the same device we should regroup and optimize
      biggest optimization, though, will come after minor Commando enhancements
      would allow feeding entire list into a single run()
    """
    if DEBUG:
        print '-->get_jobs('+str(opts)+')'
    work = []
    if opts.device_path:
        # If using device-path, then each device gets a customized list of
        # commands so we have to iterate over the devices and call Commando for
        # each device.
        path = opts.device_path
        if VERBOSE:
            print 'getting devicelist from path :'+(path)

        # Normalize path variable
        if not re.search('/$', path):
            path = path + '/'
        devs = get_devices_from_path(path)

        if VERBOSE:
            print '\tfound '+str(len(devs))+' devices'

        for dev in devs:
            cmds = []
            files = [path + dev]
            job = {'d': [dev],'c': cmds,'f': files}
            work.append(job)
    else:
        # If not using device-path, then devs and cmds are referenced on the
        # cmdline.
        devs = get_devices_from_opts(opts)
        cmds = opts.config
        files = opts.config_file
        work = [{'d': devs, 'c': cmds, 'f': files}]
    return work

def get_devices_from_path(path):
    """
    list devicenames = get_devices_from_path(str path)

    If path specified for devices/configs, then the list of filenames
    in dir will correspond to the list of devices.

    The contents of each file contain the config/commands to be loaded/run
    on the specific device.

    Future enhancements

    + verify that the filenames are fqdns
    + verify that the devnames exist in netdevices.xml
    """
    if DEBUG:
        print "-->get_devices_from_path("+path+")"

    devs = os.listdir(path)
    return devs

def get_list_from_file(path):
    """
    list text = get_list_from_file(str path)

    Specified file (path) will contain a list of \n-delimited items. This
    function is used for loading both configs/cmds as well as devices.
    """
    if DEBUG:
        print "-->get_list_from_file("+path+")"
    ret = []
    with open(path,'r') as fr:
        ret = fr.readlines()
    ret = [x.strip() for x in ret]
    return ret

def get_devices_from_opts(opts):
    """
    list devicenames = get_devices_from_opts(dict opts)

    User specified on cmdline either a path to a file containing a list of
    devices or an actual list. Return the list!
    """
    if DEBUG:
        print "-->get_devices_from_opts("+str(opts)+")"
    ret = []
    if len(opts.device_file)>0:
        ret = []
        for df in opts.device_file:
            devlist = get_list_from_file(df)
            for dev in devlist:
                ret.append(dev)
    else:
        ret = opts.devices 
    if VERBOSE:
        print "loaded "+str(len(ret))+" devices"
    if DEBUG:
        print "ret:"+str(ret)
    return ret

def get_commands_from_opts(opts):
    """
    list commands = get_commands_from_opts(dict opts)

    User specified on cmdline either a path to a file containing a list of
    commands/config or an actual list. Return the list!
    """
    if DEBUG:
        print "-->get_commands_from_opts("+str(opts)+")"
    ret = []
    if len(opts.config_file)>0:
        ret = []
        for cf in opts.config_file:
            cmdlist = get_list_from_file(cf)
            for cmd in cmdlist:
                ret.append(cmd)
    else:
        ret = opts.config
    if VERBOSE:
        print "loaded "+str(len(ret))+" commands"
    return ret

def do_work(work=None, action_class=None):
    """list results = do_work(list work)"""
    '''
    Cycle through the list of jobs and then actually 
    load the config onto the devices.
    '''
    if work is None:
        work = []
    if DEBUG:
        print "-->do_work("+str(work)+")"
    #work = [{'d':[],'c':[],'f':[]}]
    ret = []
    if VERBOSE:
        print_work(work)
    for job in work:
        for key in ('c', 'd', 'f') in:
        f = job['f']
        d = job['d']
        c = job['c']
        # **These next 2 lines do all the real work for this tool**
        n = action_class(devices=d, files=f, commands=c, verbose=VERBOSE,
                        debug=DEBUG, timeout=TIMEOUT, production_only=PROD_ONLY)
        if PUSH:
            if VERBOSE:
                print "running Commando"
            n.run()
        else:
            print "** dryrun mode.  Skipping Command run***"
        for devname in n.data:
            data = n.data[devname]
            res = {'devname': devname, 'data': data}
            ret.append(res)
        del n
    return ret

def print_work(work=None):
    """
    void = do_work(list work)

    Cycle through the list of jobs and then display the work to be done.
    """
    if work is None:
        work = []

    if DEBUG:
        print "-->do_work(%r)" % work

    for i,job in enumerate(work):
        print "\n***JOB " + str(i + 1) + "***"
        f = job['f']
        d = job['d']
        c = job['c']

        if len(d) > 0:
            print "\tDevices"
            for dev in d:
                print "\t\t" + dev

        if len(f) > 0:
            print "\tLoad From Files:"
            for file in f:
                print "\t\t" + file

        if len(c) > 0:
            print "\tRun Commands:"
            for cmd in c:
                print "\t\t" + cmd

    return True

def printResults(results=None):
    """binary success = printResults(list results)"""
    if results is None:
        results = []
    if DEBUG:
        print "-->printResults(%r)" % results
    for res in results:
        devname = res['devname']
        data = res['data']
        print
        print "###"
        print "# %s" % devname
        print "###"
        for d in data:
            cmd = d['cmd']
            out = d['out']
            device = d['dev']
            print device.shortName + "# " + str(cmd)
            print out
    return True

def stage_tftp(acls, nonce):
    """
    Need to edit this for cmds, not just acls, but 
    the baisc idea is stolen from /opt/bcs/bin/load_acl
    """
    for device in devices:
        source = settings.FIREWALL_DIR + '/acl.%s' % acl
        dest = settings.TFTPROOT_DIR + '/acl.%s.%s' % (acl, nonce)
        try:
            os.stat(dest)
        except OSError:
            try:
                copyfile(source, dest)
                os.chmod(dest, 0644)
            except:
                return None
    return True

def parse_args(argv):
    def comma_cb(option, opt_str, value, parser):
        '''OptionParser callback to handle comma-separated arguments.'''
        values = value.split(',')
        try:
            getattr(parser.values, option.dest).extend(values)
        except AttributeError:
            setattr(parser.values, option.dest, values)
    parser = OptionParser(usage='%prog [options]', description='''\
insert description here.''')
    # Options to collect lists of devices and commands
    parser.add_option('-d', '--devices', type='string', action='callback', callback=comma_cb, default=[],
                      help='Comma-separated list of devices.')
    parser.add_option('-c', '--config', type='string', action='callback', callback=comma_cb, default=[],
                      help='Comma-separated list of config statements.  '
                           'If your commands have spaces, either enclose the command in " or escape the '
                           'spaces with \\')
    parser.add_option('-D', '--device-file', type='string', action='callback', callback=comma_cb, default=[],
                      help='Specify file with list of devices.')
    parser.add_option('-C', '--config-file', type='string', action='callback', callback=comma_cb, default=[],
                      help='Specify file with list of config statements.  '
                           'The file MUST be in a tftp directory (/home/tftp/<subdir>).  '
                           'The fully-qualified path MUST be specified in the argument.  '
                           'Do NOT include "conf t" or "wr mem" in your file.  '
                           '** If both -c and -C options specified, then -c will execute first, followed by -C')
    parser.add_option('-p', '--device-path', type='string', default=None,
                      help='***NOT YET IMPLEMENTED***  '
                           'Specify dir with a file named for each device.  '
                           'Contents of each file must be list of commands.  '
                           'that you want to run for the device that shares its name with the file.  '
                           '** May NOT be used with -d,-c,-D,-C **')
    parser.add_option('-q', '--quiet', action='store_true',
                      help='suppress all standard output; errors/warnings still display.')
    parser.add_option('--exclude', '--except', type='string',
                      action='callback', callback=comma_cb, dest='exclude', default=[],
                      help='***NOT YET IMPLEMENTED***  '
                           'skip over devices; shell-type patterns '
                           '(e.g., "edge?-[md]*") can be used for devices; for '
                           'multiple excludes, use commas or give this option '
                           'more than once.')
    parser.add_option('-j', '--jobs', type='int', default=5,
                      help='maximum simultaneous connections (default 5).')
    parser.add_option('-t', '--timeout', type='int', default=TIMEOUT,
                      help="""Time in seconds to wait for each command to
                      complete (default %s).""" % TIMEOUT)
    # booleans below
    parser.add_option('-v','--verbose', action='store_true', default=False,
                      help='verbose output.')
    parser.add_option('-V','--debug', action='store_true', default=False,
                      help='debug output.')
    #parser.add_option('--severed-head', action='store_true', default=False,
    #                  help='display severed head.')
    parser.add_option('--push', action='store_true', default=False,
                      help='actually do stuff.  Default is False.')
    #parser.add_option('--no-cm', action='store_true',
    #                  help='do not open up a CM ticket for this load.')
    # Done arg list
    opts, args = parser.parse_args(argv)
    osucc, oerr = verifyopts(opts)
    setGlobalsFromOpts(opts)
    if not osucc:
        print oerr
        parser.print_help()
        sys.exit(1)
    if opts.quiet:
        sys.stdout = NullDevice()
    return opts, args

def verifyopts(opts):
    '''
    returns True if all is good
    returns False,errormsg if not
    '''
    succ = True
    err = ''
    isd = (len(opts.devices)>0)
    isc = (len(opts.config)>0)
    isdf = (len(opts.device_file)>0)
    iscf = (len(opts.config_file)>0)
    isp = (opts.device_path != None)
    if isp:
        if not os.path.isdir(opts.device_path):
            return False,'ERROR: '+path+' is not a valid path\n'
        else:
            return True,''
    elif isdf or iscf or isd or isc:
        '''
        return False, "ERROR: Sorry, but only --device-path is supported at this time\n"
        '''
    if isdf:
        for df in opts.device_file:
            if not os.path.exists(df):
                succ = False
                err = err + "ERROR: file: "+df+" does not exist\n"
    if iscf:
        for cf in opts.config_file:
            if not os.path.exists(cf):
                succ = False
                err = err + "ERROR: file: "+cf+" does not exist\n"
    if not isd and not isdf:
        succ = False
        err = err + "ERROR: You need to specify a device or two\n"
    if not isc and not iscf:
        succ = False
        err = err + "ERROR: You need to specify a command or two\n"
    '''
        One option here would be to take opts.config, write to file,
        and convert that to opts.config_file
        That way, the rest of the script only has to care about one type
        of input.
    '''
    return succ,err

def setGlobalsFromOpts(opts):
    global DEBUG
    global VERBOSE
    global PUSH
    global TIMEOUT
    DEBUG = opts.debug
    VERBOSE = opts.verbose
    PUSH = opts.push
    TIMEOUT = opts.timeout

