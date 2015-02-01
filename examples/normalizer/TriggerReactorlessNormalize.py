#!/usr/bin/python

from trigger.netdevices import NetDevices
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import defer, task, reactor
import os
import re
import sys
import time
from pinger import Pinger

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

	# def to_cisco(self, device, commands=None, extra=None):
	# 	#Perform a ping test to validate the availability of a host, 
	# 	#I'm pretty confident this is the best place to do it but I 
	# 	#can't get it to exit before connecting to the device
	# 	#another option would be to create a Twisted pre-process
	
	# 	print "In to_cisco for device {}".format(device)
	# 	if not device.is_reachable():
	# 		print "Can't ping device {}, if only I could stop it!".format(device)
	# 		print type(self)
	# 		print dir(self)
	# 		return []
	# 	else:
	# 		print "Processing device {}, it's reachable!".format(device)
	# 		return commands

	def errback(self, failure, device):
		print "Error in getRouterDetails for device {}\n{}".format(device,failure.getTraceback())

	# def select_next_device(self, jobs=None):
	#	# This seemed a clean approach , but it's still processed serially, 
	#	# it does allow other jobs to run once one of them pings clean
	#	# Currently there's a bug where it tries to pop none, it will perform 
	#	# badly if you have a number of devices that don't respond in a row
	# 
	#  	if jobs is None:
	# 		jobs = self.jobs

	# 	device = jobs.pop()

	# 	while not device.is_reachable():
	# 		print "Device {} is not reachable, not processing".format(device)
	# 		device=jobs.pop()

	# 	return device

def validateRouterDetails(result):
	print "Validating router details"
	devicesToCorrect = []

	for device, results in result.items():
		# print "Processing result set for device {}".format(device)
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
			print "Will normalized trigger-test acl on device {}".format(device)
		if routers[device].normalizeRequired:
			if routers[device].normalize["trigger_acl"]:
				devicesToCorrect.append(device)
				routers[device].commands+=["ip access-list standard trigger-test-1","permit 1.1.1.1"]
			pre_commands=["write mem","reload in 5","y","conf t"]
			post_commands=["end","reload cancel","write mem"]
			routers[device].commands=pre_commands+routers[device].commands+post_commands
			# print "Commands to run on device {} are {}".format(device,routers[device].commands)

	return devicesToCorrect or None

def initiateRouterNormalization(devices):
	# log.startLogging(sys.stdout, setStdout=False)
	if devices is not None:
		print "Normalizing {} devices ({})".format(len(devices)," ".join(devices))
		deferreds = []
		for device in devices:
			if routers[device].normalizeRequired:
				routers[device].commando = ReactorlessCommando([device],commands=routers[device].commands)
				deferreds.append(routers[device].commando.run())
		return defer.DeferredList(deferreds)
	else:
		print "No devices need to be normalized"
	return None

	def errback(self, failure, device):
		print "Error in initiateRouterNormalization for device {}\n{}".format(device,failure.getTraceback())

def stop_reactor(result):
	if reactor.running:
		reactor.stop()
		return result 

if __name__ == '__main__':
	nd = NetDevices()
	up_device_list = []
	routers={}

	# Accept a list of routers and argument or parse test-units.csv
	if len(sys.argv) > 1:
		device_list = sys.argv[1:]
	else:
		print "Processing all sites"
		with open('test-units.csv', 'rb') as csvfile:
			spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
			for row in spamreader:
				device_list.append(row[0])

	device_list = map(lambda x:x.lower(),device_list)

	print "Ping testing {} devices ({})".format(len(device_list)," ".join(device_list))

	ping = Pinger()
	ping.thread_count = 8
	ping.hosts = device_list

	up_device_list = ping.start()

	print "Processing responsive {} devices ({})".format(len(up_device_list)," ".join(up_device_list))

	# Skip Ping

	# up_device_list = device_list


	for device in up_device_list:
		routers[device]=Router(device)

	# log.startLogging(sys.stdout, setStdout=False)

	d = getRouterDetails(up_device_list).run()
	d.addCallback(validateRouterDetails)
	d.addCallback(initiateRouterNormalization)
	d.addBoth(stop_reactor)

	reactor.run()

	if d.result is not None:
		for (state,output) in d.result:
			for device in output:
				print "Device {} job state is {}".format(device,state)
