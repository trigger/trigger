# Normalizer

This example version of a Normalizer will connect to a defined set of routers. It will validate the configuration (in this case, the presence of ip access-list standard trigger-test-1), and effect a change to the device if required.

Here is the result of two executions against a set of three routers, one of which requires normalization and one of which is offline. There is a third execution where a specific router is specified on the command line. By default all routers in test-units.csv will be processed.

```
johnf@pstanadm1:~/TriggerOpen$ ./Normalize.py
Processing all sites
Are you certain you want to normalize 3 devices? [y/N]
y
Processing 3 devices (r1 r2 r3)
Failed to ping host r1
Validating router details
r2: Will normalized trigger-test acl on device
Normalizing 1 devices (r2)
Device r2: Configuration Saved
johnf@pstanadm1:~/TriggerOpen$ ./Normalize.py r2
Processing 1 devices (r2)
Validating router details
No devices need to be normalized
```

# Report

This example of a reporting tool reports on the IOS version of devices. If you run it without specifing a device it will connect to all devices in test-units.csv. If you specify devices it will only connect to them. The report.csv file that it creates also indicates when the device was last contacted.

```
johnf@pstanadm1:~/TriggerOpen$ ./Report.py 
Processing all sites
Failed to ping host r1
johnf@pstanadm1:~/TriggerOpen$ cat report.csv 
Device,Last Access,Version
r1,Never,Unknown
r2,2015-08-20 09:00,15.2(4)M6
r3,2015-08-20 09:00,15.2(4)M6
johnf@pstanadm1:~/TriggerOpen$ date
Thu Aug 20 09:00:56 EDT 2015
johnf@pstanadm1:~/TriggerOpen$ date
Thu Aug 20 09:00:58 EDT 2015
johnf@pstanadm1:~/TriggerOpen$ date
Thu Aug 20 09:01:00 EDT 2015
johnf@pstanadm1:~/TriggerOpen$ ./Report.py r2
johnf@pstanadm1:~/TriggerOpen$ cat report.csv 
Device,Last Access,Version
r1,Never,Unknown
r2,2015-08-20 09:01,15.2(4)M6
r3,2015-08-20 09:00,15.2(4)M6
```


# ToDo


