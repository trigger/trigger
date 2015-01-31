# Normalizer

This example version of a Normalizer will connect to a defined set of routers. It will validate the configuration (in this case, the presence of ip access-list standard trigger-test-1), and effect a change to the device if required. In the environment where this script is used, working with remote CPEs, a reload is preferred to loss of device connectivity. This probably isn't the case for most environments.

There are a number of todos, the most signficiant is that I would like to return the ordered command output including commands that occur more than once (e.g. write mem).

Here is a first execution against a set of three routers, one of which requires normalization and one of which is offline.

```
johnf@pstanadm1:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
Error in getRouterDetails for device r3
Traceback (most recent call last):
Failure: twisted.internet.error.ConnectError: An error occurred while connecting: 113: No route to host.

In validateRouterDetails
Processing result set for device r1
Processing result set for device r2
In initiateRouterNormalization
Will normalize router r1 
Need to normalize ACL on router r1
Job state is True
Device r1
```

And a second execution with the configurations normalized.

```
johnf@pstanadm1:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
Error in getRouterDetails for device r3
Traceback (most recent call last):
Failure: twisted.internet.error.ConnectError: An error occurred while connecting: 113: No route to host.

In validateRouterDetails
Processing result set for device r1
Processing result set for device r2
In initiateRouterNormalization
No devices need to be normalized
```