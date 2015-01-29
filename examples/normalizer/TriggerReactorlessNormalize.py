#!/usr/bin/python

from trigger.netdevices import NetDevices
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import defer, task, reactor
import re
import sys
import time

class Router(object):
	def __init__(self, name):
		self.name = name
		self.acls = []
		self.normalize = {}
		self.normalizeRequired = False
		self.commands = []
		self.commando = None

class getRouterDetails(ReactorlessCommando):
	commands = ['show run | i ip access-list']

def validateRouterDetails(result):
	print "In validateRouterDetails"
	devicesToCorrect = []

	for device, results in result.items():
		print "Processing result set for device {}".format(device)
		routers[device].normalize["trigger_acl"] = True
		for line in results["show run | i ip access-list"].splitlines():
			line=line.strip()
			m = re.search("ip access-list \S+ (\S+)",line)
			if m is not None:
				routers[device].acls.append(m.group(1))
			m = re.search("ip access-list standard trigger-test-1",line)
			if m is not None:
				routers[device].normalize["trigger_acl"] = False
		
		# Because there is a negative test for the presence of the ACL we need to set normalizeRequired=True here, it would normally be done inside the test for a rule
		if routers[device].normalize["trigger_acl"]:
			routers[device].normalizeRequired=True
		if routers[device].normalizeRequired:
			if routers[device].normalize["trigger_acl"]:
				devicesToCorrect.append(device)
				routers[device].commands+=["conf t","ip access-list standard trigger-test-1","permit 1.1.1.1","end"]
				routers[device].commands.insert(0,"write mem")
				routers[device].commands.insert(1,"reload in 5")
				routers[device].commands.insert(2,"y")
				routers[device].commands.append("reload cancel")
				routers[device].commands.append("write mem")
			print "Commands to run on device {} are {}".format(device,routers[device].commands)

	return devicesToCorrect or None

def initiateRouterNormalization(devices):
	print "In initiateRouterNormalization"
	# log.startLogging(sys.stdout, setStdout=False)
	if devices is not None:
		deferreds = []
		for device in devices:
			print "Will normalize router {} ".format(device)
			if routers[device].normalize["trigger_acl"]:
				print "Need to normalize ACL on router {}".format(device)
				routers[device].commando = ReactorlessCommando([device],commands=routers[device].commands)
				deferreds.append(routers[device].commando.run())
		return defer.DeferredList(deferreds)
	else:
		print "No devices need to be normalized"

	return None

def stop_reactor(result):
	if reactor.running:
		reactor.stop()
		return result 

if __name__ == '__main__':
	nd = NetDevices()
	device_list = ['r1', 'r2']
	routers={}

	for device in device_list:
		routers[device]=Router(device)

	# log.startLogging(sys.stdout, setStdout=False)

	d = getRouterDetails(device_list).run()
	d.addCallback(validateRouterDetails)
	d.addCallback(initiateRouterNormalization)
	d.addBoth(stop_reactor)

	reactor.run()

	print d.result

	if d.result is not None:
		for (state,output) in d.result:
			print "Job state is {}".format(state)
			for device in output:
				print "Device {}".format(device)
				for command in output[device]:
					print "Command: {}".format(command)
					print "Output: {}".format(output[device][command])