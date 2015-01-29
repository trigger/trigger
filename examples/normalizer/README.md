# Normalizer

This example version of a Normalizer will connect to a defined set of routers. It will validate the configuration (in this case, the presence of ip access-list standard trigger-test-1), and effect a change to the device if required. In the environment where this script is used, working with remote CPEs, a reload is preferred to loss of device connectivity. This probably isn't the case for most environments.

There are a number of todos, the most signficiant is that the command output isn't ordered (and has piles of extra carriage returns, appears to be broken in more than one way)

Here is a first execution against a set of two routers, one of which requires normalization.

```
johnf@triggertest:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
In validateRouterDetails
Processing result set for device r1
Commands to run on device r1 are ['write mem', 'reload in 5', 'y', 'conf t', 'ip access-list standard trigger-test-1', 'permit 1.1.1.1', 'end', 'reload cancel', 'write mem']
Processing result set for device r2
In initiateRouterNormalization
Will normalize router r1 
Need to normalize ACL on router r1
[(True, {'r1': {'reload in 5': '', 'end': '', 'permit 1.1.1.1': '', 'reload cancel': '', 'conf t': '', 'y': '', 'write mem': '', 'ip access-list standard trigger-test-1': 'Enter configuration commands, one per line.  End with CNTL/Z.\r\n'}})]
Job state is True
Device r1
Command: reload in 5
Output: 
Command: end
Output: 
Command: permit 1.1.1.1
Output: 
Command: reload cancel
Output: 
Command: conf t
Output: 
Command: y
Output: 
Command: write mem
Output: 
Command: ip access-list standard trigger-test-1
Output: Enter configuration commands, one per line.  End with CNTL/Z.

```

And a second execution with the configurations normalized.

```
johnf@triggertest:~/TriggerTest$ ./TriggerReactorlessNormalize.py 
In validateRouterDetails
Processing result set for device r1
Processing result set for device r2
In initiateRouterNormalization
No devices need to be normalized
None
```