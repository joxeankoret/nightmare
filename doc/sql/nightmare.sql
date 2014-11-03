-- MySQL dump 10.13  Distrib 5.5.32, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: nightmare
-- ------------------------------------------------------
-- Server version	5.5.32-0ubuntu0.12.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `config`
--

DROP TABLE IF EXISTS `config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config` (
  `config_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `value` varchar(300) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `date` date DEFAULT NULL,
  PRIMARY KEY (`config_id`),
  UNIQUE KEY `idx_uq_config_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `crash_data`
--

DROP TABLE IF EXISTS `crash_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `crash_data` (
  `crash_data_id` int(11) NOT NULL AUTO_INCREMENT,
  `crash_id` int(11) NOT NULL,
  `type` varchar(30) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  `date` datetime DEFAULT NULL,
  PRIMARY KEY (`crash_data_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `crashes`
--

DROP TABLE IF EXISTS `crashes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `crashes` (
  `crash_id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `sample_id` int(11) NOT NULL,
  `program_counter` varchar(18) DEFAULT NULL,
  `crash_signal` varchar(30) DEFAULT NULL,
  `exploitability` varchar(100) DEFAULT NULL,
  `disassembly` varchar(255) DEFAULT NULL,
  `date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `total_samples` int(11) NOT NULL,
  `additional` mediumtext,
  PRIMARY KEY (`crash_id`)
) ENGINE=InnoDB AUTO_INCREMENT=826 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `diffs`
--

DROP TABLE IF EXISTS `diffs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `diffs` (
  `diff_id` int(11) NOT NULL AUTO_INCREMENT,
  `sample_id` int(11) NOT NULL,
  `bytes` varbinary(255) DEFAULT NULL,
  `action` int(11) DEFAULT NULL,
  PRIMARY KEY (`diff_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mutation_engines`
--

DROP TABLE IF EXISTS `mutation_engines`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mutation_engines` (
  `mutation_engine_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `command` varchar(255) DEFAULT NULL,
  `enabled` tinyint(1) DEFAULT '1',
  `date` date DEFAULT NULL,
  PRIMARY KEY (`mutation_engine_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `mutation_engines` WRITE;
/*!40000 ALTER TABLE `mutation_engines` DISABLE KEYS */;
INSERT INTO `mutation_engines` VALUES (1,'Radamsa','Radamsa is a test case generator for robustness testing, aka a fuzzer.\r\n\r\nMay or may not preserve input size.\r\n\r\nhttps://code.google.com/p/ouspg/wiki/Radamsa\r\n','radamsa %INPUT% -o %OUTPUT%',1,'2013-05-20'),(2,'Charlie Miller Algo.','Python implementation of the random based fuzzing algorithm presented by Charlie Miller in CSW2010. Preserves input size.','%NIGHTMARE_PATH%/mutators/cmiller_mutator.py %INPUT% %OUTPUT%',1,'2013-05-20'),(3,'Charlie Miller REP Algo.','Similar to Charlie Miller\'s algorithm but generating repetitions of the same random byte. Preserves input size.','%NIGHTMARE_PATH%/mutators/cmiller_mutator_rep.py %INPUT% %OUTPUT%',1,'2013-05-20'),(4,'Radamsa multiple','This is a wrapper using Radamsa to create a zip file with multiple fuzzed samples inside. This is useful, for example, to fuzz Antivirus engines.\r\n','%NIGHTMARE_PATH%/mutators/radamsa_multiple.py %TEMPLATES_PATH%/%FOLDER% 10 %OUTPUT%',1,'2013-08-12'),(5,'Radamsa multiple big','This is a wrapper using Radamsa to create a zip file with multiple fuzzed samples inside. This is useful, for example, to fuzz Antivirus engines.\r\n\r\nIt creates zip files with 30 samples inside.','%NIGHTMARE_PATH%/mutators/radamsa_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2013-08-13'),(6,'Simple replacer','This is a very näive algorithm: it simply choose a random position in the input file, choose a random character and a random size and replaces a chunk of data with the selected character repeated for the size selected. That\'s all. It preserves input size and creates a diff file for the mutated file.','%NIGHTMARE_PATH%/mutators/simple_replacer.py %INPUT% %OUTPUT%',1,'2013-08-14'),(7,'Simple replacer mutiple','Same as \"Simple replacer\" but fuzzing many files (30) and zipping all of them. It also saves .diff files for the mutated files.','%NIGHTMARE_PATH%/mutators/simple_replacer_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2013-08-14'),(8,'Charlie Miller multiple','Same as \"Charlie Miller Algo.\" but fuzzing many files (30) and zipping all of them. It also saves .diff files for the mutated files.','%NIGHTMARE_PATH%/mutators/cmiller_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2014-05-05'),(9,'Zzuf','Zzuf mutator. Preserves input size.\r\nhttp://caca.zoy.org/wiki/zzuf','%NIGHTMARE_PATH%/mutators/zzuf_mutator.py %INPUT% %OUTPUT%',1,'2014-05-10'),(10,'Zzuf multiple','This is a wrapper using Zzuf mutator to create a zip file with multiple fuzzed samples inside. Useful to fuzz Antivirus engines.','%NIGHTMARE_PATH%/mutators/zzuf_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 20 %OUTPUT%',1,'2014-05-10'),(11,'MachO mutator','Half intelligent MachO fuzzer. It only supports a few fields for some headers but, anyway, it should be enough to discover some bugs.','%NIGHTMARE_PATH%/mutators/macho_mutator.py %INPUT% %OUTPUT%',1,'2014-06-29');
/*!40000 ALTER TABLE `mutation_engines` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

--
-- Table structure for table `project_engines`
--

DROP TABLE IF EXISTS `project_engines`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `project_engines` (
  `project_engine_id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `mutation_engine_id` int(11) NOT NULL,
  PRIMARY KEY (`project_engine_id`),
  UNIQUE KEY `project_id` (`project_id`,`mutation_engine_id`)
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projects`
--

DROP TABLE IF EXISTS `projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `projects` (
  `project_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `subfolder` varchar(255) DEFAULT NULL,
  `tube_prefix` varchar(50) DEFAULT NULL,
  `maximum_samples` int(11) NOT NULL DEFAULT '100',
  `maximum_iteration` int(11) NOT NULL DEFAULT '1000000',
  `enabled` tinyint(1) DEFAULT '1',
  `archived` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `samples`
--

DROP TABLE IF EXISTS `samples`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `samples` (
  `sample_id` int(11) NOT NULL AUTO_INCREMENT,
  `engine_id` int(11) NOT NULL,
  `template_hash` varchar(40) DEFAULT NULL,
  `sample_hash` varchar(40) DEFAULT NULL,
  `date` datetime DEFAULT NULL,
  PRIMARY KEY (`sample_id`)
) ENGINE=InnoDB AUTO_INCREMENT=839 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `statistics`
--

DROP TABLE IF EXISTS `statistics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `statistics` (
  `statistic_id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `mutation_engine_id` int(11) NOT NULL,
  `total` int(11) NOT NULL DEFAULT '0',
  `iteration` int(11) NOT NULL DEFAULT '0',
  `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`statistic_id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-09-14 16:14:58
-- MySQL dump 10.13  Distrib 5.5.32, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: nightmare
-- ------------------------------------------------------
-- Server version	5.5.32-0ubuntu0.12.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `config`
--

DROP TABLE IF EXISTS `config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config` (
  `config_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `value` varchar(300) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `date` date DEFAULT NULL,
  PRIMARY KEY (`config_id`),
  UNIQUE KEY `idx_uq_config_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config`
--

LOCK TABLES `config` WRITE;
/*!40000 ALTER TABLE `config` DISABLE KEYS */;
INSERT INTO `config` VALUES (7,'SAMPLES_PATH','/home/joxean/Documentos/research/nightmare/results',NULL,NULL),(8,'TEMPLATES_PATH','/home/joxean/Documentos/research/nightmare/samples',NULL,NULL),(9,'NIGHTMARE_PATH','/home/joxean/Documentos/research/nightmare',NULL,NULL),(10,'QUEUE_HOST','localhost',NULL,NULL),(11,'QUEUE_PORT','11300',NULL,NULL);
/*!40000 ALTER TABLE `config` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-09-14 16:15:43
