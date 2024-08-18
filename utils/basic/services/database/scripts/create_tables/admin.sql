CREATE TABLE IF NOT EXISTS analytics_commands_all_time
(
    command VARCHAR(64),
    uses    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS analytics_commands_per_day
(
    command VARCHAR(64),
    uses    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS analytics_logs
(
    id   SERIAL,
    type VARCHAR(255),
    date VARCHAR(255),
    args VARCHAR(255)
);