--
-- Table structure for table `acl_queue`
--
-- This is the "integrated" queue used by trigger.acl.db.Queue, eg `acl -l`
--
CREATE TABLE acl_queue (
      acl           VARCHAR NOT NULL DEFAULT '',
      router        VARCHAR NOT NULL DEFAULT '',
      queued        DATETIME DEFAULT CURRENT_DATETIME,
      loaded        DATETIME NULL,
      escalation    TINYINT NOT NULL DEFAULT 0
);

-- CREATE TABLE queue (
      -- `q_ts` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
      -- `q_id` int(11) NOT NULL auto_increment,
      -- `q_name` text NOT NULL,
      -- `q_routers` varchar(255) NOT NULL default '',
      -- `done` tinyint(1) NOT NULL default '0',
      -- `q_sr` int(11) NOT NULL default '0',
      -- `login` varchar(32) NOT NULL default '',
--       PRIMARY KEY  (`q_id`)
-- )
