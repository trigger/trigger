--
-- Table structure for table `netdevices`
--
-- This is for 'netdevices.sql' SQLite support within
-- trigger.netdevices.NetDevices for storing and tracking network device
-- metadata.
--
-- This is based on the current set of existing attributes in use and is by no
-- means exclusive. Feel free to add your own fields to suit your environment.
--

CREATE TABLE netdevices (
    id  INTEGER PRIMARY KEY,
    OOBTerminalServerConnector VARCHAR(1024),
    OOBTerminalServerFQDN VARCHAR(1024),
    OOBTerminalServerNodeName VARCHAR(1024),
    OOBTerminalServerPort VARCHAR(1024),
    OOBTerminalServerTCPPort VARCHAR(1024),
    acls VARCHAR(1024),
    adminStatus VARCHAR(1024),
    assetID VARCHAR(1024),
    authMethod VARCHAR(1024),
    barcode VARCHAR(1024),
    budgetCode VARCHAR(1024),
    budgetName VARCHAR(1024),
    bulk_acls VARCHAR(1024),
    connectProtocol VARCHAR(1024),
    coordinate VARCHAR(1024),
    deviceType VARCHAR(1024),
    enablePW VARCHAR(1024),
    explicit_acls VARCHAR(1024),
    gslb_master VARCHAR(1024),
    implicit_acls VARCHAR(1024),
    lastUpdate VARCHAR(1024),
    layer2 VARCHAR(1024),
    layer3 VARCHAR(1024),
    layer4 VARCHAR(1024),
    lifecycleStatus VARCHAR(1024),
    loginPW VARCHAR(1024),
    make VARCHAR(1024),
    manufacturer VARCHAR(1024),
    model VARCHAR(1024),
    nodeName VARCHAR(1024),
    onCallEmail VARCHAR(1024),
    onCallID VARCHAR(1024),
    onCallName VARCHAR(1024),
    operationStatus VARCHAR(1024),
    owner VARCHAR(1024),
    owningTeam VARCHAR(1024),
    projectID VARCHAR(1024),
    projectName VARCHAR(1024),
    room VARCHAR(1024),
    serialNumber VARCHAR(1024),
    site VARCHAR(1024)
);
