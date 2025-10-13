-- Creates 10 compression-test tables and 10 archive-test tables.
-- Variables provided by beeline: DB, PREFIX

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

CREATE DATABASE IF NOT EXISTS ${hivevar:DB};
USE ${hivevar:DB};

-- Compression test tables (partitioned by dt)
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_01 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_02 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_03 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_04 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_05 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_06 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_07 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_08 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_09 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_compress_10 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

-- Archive test tables (partitioned by dt)
CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_01 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_02 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_03 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_04 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_05 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_06 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_07 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_08 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_09 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

CREATE EXTERNAL TABLE IF NOT EXISTS ${hivevar:PREFIX}_archive_10 (
  id BIGINT,
  name STRING,
  payload STRING,
  ts TIMESTAMP
) PARTITIONED BY (dt STRING)
STORED AS TEXTFILE
TBLPROPERTIES (
  'transactional'='false',
  'external.table.purge'='true'
);

-- Optionally, create one empty partition for quick validation
-- You can duplicate these INSERTs to create more partitions/files.
INSERT OVERWRITE TABLE ${hivevar:PREFIX}_compress_01 PARTITION (dt='2025-09-18')
SELECT 1, 'demo', 'payload', from_unixtime(unix_timestamp());

INSERT OVERWRITE TABLE ${hivevar:PREFIX}_archive_01 PARTITION (dt='2025-09-18')
SELECT 1, 'demo', 'payload', from_unixtime(unix_timestamp());

