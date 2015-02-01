#!/usr/bin/python

# Ping Stuff

import subprocess
import threading

class Pinger(object):
	hosts = [] # List of all hosts/ips in our input queue
	up_hosts =[]

	# How many ping process at the time.
	thread_count = 4

	# Lock object to keep track the threads in loops, where it can potentially be race conditions.
	lock = threading.Lock()

	def ping(self, ip):
		# Use the system ping command with count of 1 and wait time of 1.
		ret = subprocess.call(['ping', '-c', '3', '-W', '2', ip],
							  stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))

		return ret == 0 # Return True if our ping command succeeds

	def pop_queue(self):
		ip = None

		self.lock.acquire() # Grab or wait+grab the lock.

		if self.hosts:
			ip = self.hosts.pop()

		self.lock.release() # Release the lock, so another thread could grab it.

		return ip

	def dequeue(self):
		while True:
			ip = self.pop_queue()

			if not ip:
				return None

			if self.ping(ip):
				self.up_hosts.append(ip)
			else:
				print "Failed to ping host {}".format(ip)

	def start(self):
		threads = []

		for i in range(self.thread_count):
			# Create self.thread_count number of threads that together will
			# cooperate removing every ip in the list. Each thread will do the
			# job as fast as it can.
			t = threading.Thread(target=self.dequeue)
			t.start()
			threads.append(t)

		# Wait until all the threads are done. .join() is blocking.
		[ t.join() for t in threads ]

		return self.up_hosts

# Actual Trigger Stuff

from trigger.netdevices import NetDevices
from trigger.cmds import ReactorlessCommando
from twisted.python import log
from twisted.internet import defer, task, reactor
import os
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

	# def _setup_jobs(self):
	#	# This does not work well, it's a serial process
	# 	for device in self.devices:
	# 		print "Processing device {}".format(device)
	# 		try:
	# 			devobj = self.nd.find(str(device))
	# 		except KeyError:
	# 			print 'Device not found in NetDevices: {}'.format(device)
	# 			self.devices.remove(device)
	# 			continue
	# 		if not devobj.is_reachable():
	# 			print "Device {} is not reachable, not processing".format(device)
	# 			self.devices.remove(device)

	# 	return super(getRouterDetails, self)._setup_jobs()


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
	device_list = ['r1', 'r2', 'r3']
	up_device_list = []
	routers={}
	device_list = map(lambda x:x.lower(),device_list)

	# This will ping devices before connecting 

	# print "Ping testing {} devices ({})".format(len(device_list)," ".join(device_list))

	# for device in device_list:
	# 	response = os.system("ping -c 2 {} >/dev/null 2>&1".format(device))
	# 	if response == 0:
	# 		up_device_list.append(device)
	# 	else:
	# 		print "Not processing device {}, failed to responded to ping".format(device)

	# print "Processing responsive {} devices ({})".format(len(up_device_list)," ".join(up_device_list))

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
