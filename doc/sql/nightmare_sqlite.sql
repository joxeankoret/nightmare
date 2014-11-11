PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE `crash_data` (
  `crash_data_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `crash_id` int(11) NOT NULL,
  `type` varchar(30) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `value` varchar(255) DEFAULT NULL,
  `date` datetime DEFAULT NULL
);
CREATE TABLE `crashes` (
  `crash_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `project_id` int(11) NOT NULL,
  `sample_id` int(11) NOT NULL,
  `program_counter` varchar(18) DEFAULT NULL,
  `crash_signal` varchar(30) DEFAULT NULL,
  `exploitability` varchar(100) DEFAULT NULL,
  `disassembly` varchar(255) DEFAULT NULL,
  `date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `total_samples` int(11) NOT NULL,
  `additional` mediumtext
);
CREATE TABLE `diffs` (
  `diff_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `sample_id` int(11) NOT NULL,
  `bytes` varbinary(255) DEFAULT NULL,
  `action` int(11) DEFAULT NULL
);
CREATE TABLE `mutation_engines` (
  `mutation_engine_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `command` varchar(255) DEFAULT NULL,
  `enabled` tinyint(1) DEFAULT '1',
  `date` date DEFAULT NULL
);
INSERT INTO "mutation_engines" VALUES(1,'Radamsa','Radamsa is a test case generator for robustness testing, aka a fuzzer.\r\n\r\nMay or may not preserve input size.\r\n\r\nhttps://code.google.com/p/ouspg/wiki/Radamsa\r\n','radamsa %INPUT% -o %OUTPUT%',1,'2013-05-20');
INSERT INTO "mutation_engines" VALUES(2,'Charlie Miller Algo.','Python implementation of the random based fuzzing algorithm presented by Charlie Miller in CSW2010. Preserves input size.','%NIGHTMARE_PATH%/mutators/cmiller_mutator.py %INPUT% %OUTPUT%',1,'2013-05-20');
INSERT INTO "mutation_engines" VALUES(3,'Charlie Miller REP Algo.','Similar to Charlie Miller''s algorithm but generating repetitions of the same random byte. Preserves input size.','%NIGHTMARE_PATH%/mutators/cmiller_mutator_rep.py %INPUT% %OUTPUT%',1,'2013-05-20');
INSERT INTO "mutation_engines" VALUES(4,'Radamsa multiple','This is a wrapper using Radamsa to create a zip file with multiple fuzzed samples inside. This is useful, for example, to fuzz Antivirus engines.\r\n','%NIGHTMARE_PATH%/mutators/radamsa_multiple.py %TEMPLATES_PATH%/%FOLDER% 10 %OUTPUT%',1,'2013-08-12');
INSERT INTO "mutation_engines" VALUES(5,'Radamsa multiple big','This is a wrapper using Radamsa to create a zip file with multiple fuzzed samples inside. This is useful, for example, to fuzz Antivirus engines.\r\n\r\nIt creates zip files with 30 samples inside.','%NIGHTMARE_PATH%/mutators/radamsa_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2013-08-13');
INSERT INTO "mutation_engines" VALUES(6,'Simple replacer','This is a very näive algorithm: it simply choose a random position in the input file, choose a random character and a random size and replaces a chunk of data with the selected character repeated for the size selected. That''s all. It preserves input size and creates a diff file for the mutated file.','%NIGHTMARE_PATH%/mutators/simple_replacer.py %INPUT% %OUTPUT%',1,'2013-08-14');
INSERT INTO "mutation_engines" VALUES(7,'Simple replacer mutiple','Same as \"Simple replacer\" but fuzzing many files (30) and zipping all of them. It also saves .diff files for the mutated files.','%NIGHTMARE_PATH%/mutators/simple_replacer_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2013-08-14');
INSERT INTO "mutation_engines" VALUES(8,'Charlie Miller multiple','Same as \"Charlie Miller Algo.\" but fuzzing many files (30) and zipping all of them. It also saves .diff files for the mutated files.','%NIGHTMARE_PATH%/mutators/cmiller_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 30 %OUTPUT%',1,'2014-05-05');
INSERT INTO "mutation_engines" VALUES(9,'Zzuf','Zzuf mutator. Preserves input size.\r\nhttp://caca.zoy.org/wiki/zzuf','%NIGHTMARE_PATH%/mutators/zzuf_mutator.py %INPUT% %OUTPUT%',1,'2014-05-10');
INSERT INTO "mutation_engines" VALUES(10,'Zzuf multiple','This is a wrapper using Zzuf mutator to create a zip file with multiple fuzzed samples inside. Useful to fuzz Antivirus engines.','%NIGHTMARE_PATH%/mutators/zzuf_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 20 %OUTPUT%',1,'2014-05-10');
INSERT INTO "mutation_engines" VALUES(11,'MachO mutator','Half intelligent MachO fuzzer. It only supports a few fields for some headers but, anyway, it should be enough to discover some bugs.','%NIGHTMARE_PATH%/mutators/macho_mutator.py %INPUT% %OUTPUT%',1,'2014-06-29');
INSERT INTO "mutation_engines" VALUES(12, 'OLE2 Mutator', 'OLE2 streams mutator. It uses the Python library OleFileIO_PL from https://bitbucket.org/decalage/olefileio_pl.', '%NIGHTMARE_PATH%/mutators/ole_file_mutator.py %INPUT% %OUTPUT%', 1, '2014-08-07');
INSERT INTO "mutation_engines" VALUES(13, 'OLE2 mutator multiple', 'Same as OLE2 mutator but creating a bundle with many (10) files inside.', '%NIGHTMARE_PATH%/mutators/ole_file_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 10 %OUTPUT%', 1, '2014-08-07');
insert into "mutation_engines" values (14, 'Melkor mutator', 'Melkor is a very intuitive and easy-to-use ELF file format fuzzer to find functional and security bugs in ELF parsers.' , '%NIGHTMARE_PATH%/mutators/melkor_mutator.py %TEMPLATES_PATH%/%FOLDER% 10 %OUTPUT%', 1, '2014-11-10');
insert into "mutation_engines" values (15, 'Melkor mutator multiple', 'This is a wrapper using Melkor mutator to create a zip file with multiple fuzzed samples inside. Useful to fuzz Antivirus engines.', '%NIGHTMARE_PATH%/mutators/melkor_mutator_multiple.py %TEMPLATES_PATH%/%FOLDER% 20 %OUTPUT%', 1, '2014-11-10');
CREATE TABLE `project_engines` (
  `project_engine_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `project_id` int(11) NOT NULL,
  `mutation_engine_id` int(11) NOT NULL
);
CREATE TABLE `projects` (
  `project_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `subfolder` varchar(255) DEFAULT NULL,
  `tube_prefix` varchar(50) DEFAULT NULL,
  `maximum_samples` int(11) NOT NULL DEFAULT '100',
  `maximum_iteration` int(11) NOT NULL DEFAULT '1000000',
  `enabled` tinyint(1) DEFAULT '1',
  `archived` tinyint(1) DEFAULT '1'
);
CREATE TABLE `samples` (
  `sample_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `engine_id` int(11),
  `template_hash` varchar(40) DEFAULT NULL,
  `sample_hash` varchar(40) DEFAULT NULL,
  `date` datetime DEFAULT NULL
);
CREATE TABLE `statistics` (
  `statistic_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `project_id` int(11) NOT NULL,
  `mutation_engine_id` int(11) NOT NULL,
  `total` int(11) NOT NULL DEFAULT '0',
  `iteration` int(11) NOT NULL DEFAULT '0',
  `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE `config` (
  `config_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` varchar(30) DEFAULT NULL,
  `value` varchar(300) DEFAULT NULL,
  `description` varchar(300) DEFAULT NULL,
  `date` date DEFAULT NULL
);
INSERT INTO "config" VALUES(7,'SAMPLES_PATH','/home/joxean/Documentos/research/nightmare/results',NULL,NULL);
INSERT INTO "config" VALUES(8,'TEMPLATES_PATH','/home/joxean/Documentos/research/nightmare/samples',NULL,NULL);
INSERT INTO "config" VALUES(9,'NIGHTMARE_PATH','/home/joxean/Documentos/research/nightmare',NULL,NULL);
INSERT INTO "config" VALUES(10,'QUEUE_HOST','localhost',NULL,NULL);
INSERT INTO "config" VALUES(11,'QUEUE_PORT','11300',NULL,NULL);
DELETE FROM sqlite_sequence;
INSERT INTO "sqlite_sequence" VALUES('mutation_engines',11);
INSERT INTO "sqlite_sequence" VALUES('config',11);
CREATE UNIQUE INDEX `project_id` on project_engines (`project_id`,`mutation_engine_id`);
CREATE UNIQUE INDEX idx_uq_config_name on config (`name`);
COMMIT;
