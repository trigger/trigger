--
-- Table structure for table `acl_queue`
--
-- This is the "integrated" queue used by trigger.acl.db.Queue, eg `acl -l`
--

SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
CREATE TABLE `acl_queue` (
      `acl` varchar(255) collate utf8_unicode_ci NOT NULL default '',
      `router` varchar(255) collate utf8_unicode_ci NOT NULL default '',
      `queued` datetime NOT NULL default '0000-00-00 00:00:00',
      `loaded` datetime default NULL,
      `escalation` tinyint(1) NOT NULL default '0',
      KEY `loaded` (`loaded`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `queue`
--
-- This is the "manual" queue used by trigger.acl.db.Queue, e.g. `acl -m` 
--

SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
CREATE TABLE `queue` (
      `q_ts` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
      `q_id` int(11) NOT NULL auto_increment,
      `q_name` text NOT NULL,
      `q_routers` varchar(255) NOT NULL default '',
      `done` tinyint(1) NOT NULL default '0',
      `q_sr` int(11) NOT NULL default '0',
      `login` varchar(32) NOT NULL default '',
      PRIMARY KEY  (`q_id`)
) ENGINE=MyISAM AUTO_INCREMENT=247795 DEFAULT CHARSET=latin1;
SET character_set_client = @saved_cs_client;
