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
