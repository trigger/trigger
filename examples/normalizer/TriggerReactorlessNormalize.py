#!/usr/bin/python

import os
import re
import sys
import time
import csv
from trigger.netdevices import NetDevices
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import defer, task, reactor
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

	def errback(self, failure, device):
		print "Error in getRouterDetails for device {}\n{}".format(device,failure.getTraceback())

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
			pre_commands=["conf t"]
			post_commands=["end","write mem"]
			routers[device].commands=pre_commands+routers[device].commands+post_commands
			# print "Commands to run on device {} are {}".format(device,routers[device].commands)

	return devicesToCorrect or None

class normalizeRouters(ReactorlessCommando):
	def to_cisco(self, dev, commands=None, extra=None):
		dev_commands = routers[dev.nodeName].commands
		# self.commands = dev_commands
		# print "Device {}: Executing Commands:\n{}".format(dev.nodeName,dev_commands)
		return dev_commands

	def from_cisco(self, results, device):
		dev_commands = routers[device.nodeName].commands
		# print "In from_cisco for {}, storing results {} from commands {}".format(device,results,self.commands)
		log.msg('Received %r from %s' % (results, device))
		self.store_results(device, self.map_results(dev_commands, results))

	def errback(self, failure, device):
		print "Error in normalizeRouters for device {}\n{}".format(device,failure.getTraceback())


def initiateRouterNormalization(devices):
	#log.startLogging(sys.stdout, setStdout=False)
	if devices is not None:
		print "Normalizing {} devices ({})".format(len(devices)," ".join(devices))
		devicesToNormalize = []
		for device in devices:
			if routers[device].normalizeRequired:
				devicesToNormalize.append(device)
		return normalizeRouters(devicesToNormalize).run()
	else:
		print "No devices need to be normalized".format()
	return None

def stop_reactor(result):
	if reactor.running:
		reactor.stop()
		return result 

if __name__ == '__main__':
	nd = NetDevices()
	device_list=[]
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
		user_response = raw_input("Are you certain you want to normalize {} devices? [y/N]\n".format(len(device_list)))
		m = re.search ("^[yY]",user_response)
		if m is None:
			print "Aborting processing"
			exit(1)

	device_list = map(lambda x:x.lower(),device_list)

	print "Ping testing {} devices ({})".format(len(device_list)," ".join(device_list))

	ping = Pinger()
	ping.thread_count = 8
	ping.hosts = device_list

	up_device_list = ping.start()

	print "Processing responsive {} devices ({})".format(len(up_device_list)," ".join(up_device_list))


	for device in up_device_list:
		routers[device]=Router(device)

	# log.startLogging(sys.stdout, setStdout=False)

	d = getRouterDetails(up_device_list).run()
	d.addCallback(validateRouterDetails)
	d.addCallback(initiateRouterNormalization)
	d.addBoth(stop_reactor)

	reactor.run()

	if d.result is not None:
		for device in d.result.keys():
			# print "Device {}: Command Output:\n{}".format(device,d.result[device][None])
			m = re.search(r"\[OK\]",d.result[device]["write mem"])
			if m is not None:
				print "Device {}: Configuration Saved".format(device)
			else:
				print "Device {}: Warning no [OK] in Output".format(device)
