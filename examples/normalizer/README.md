# Normalizer

This example version of a Normalizer will connect to a defined set of routers. It will validate the configuration (in this case, the presence of ip access-list standard trigger-test-1), and effect a change to the device if required. In the environment where this script is used, working with remote CPEs, a reload is preferred to loss of device connectivity. This probably isn't the case for most environments.

There are a number of todos, the most signficiant is that I would like to return the ordered command output including commands that occur more than once (e.g. write mem).

Here is the result of two executions against a set of three routers, one of which requires normalization and one of which is offline.

```
johnf@pstanadm1:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
Ping testing 3 devices (r1 r2 r3)
Not processing device r3, failed to responded to ping
Processing responsive 2 devices (r1 r2)
Validating router details
Queueing routers for normalization
Will normalize router r1 
Need to normalize ACL
Job state is True
Device r1
johnf@pstanadm1:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
Ping testing 3 devices (r1 r2 r3)
Not processing device r3, failed to responded to ping
Processing responsive 2 devices (r1 r2)
Validating router details
Queueing routers for normalization
No devices need to be normalized
```