CREATE TABLE IF NOT EXISTS settings_main
(
    guild_id BIGINT,
    banner   VARCHAR(255) DEFAULT NULL,
    economy  BOOLEAN      DEFAULT TRUE,
    language VARCHAR(16)  DEFAULT 'ru'
);

CREATE TABLE IF NOT EXISTS settings_logs
(
    guild_id        BIGINT,
    server_status   BIGINT DEFAULT NULL,
    channels_status BIGINT DEFAULT NULL,
    members_status  BIGINT DEFAULT NULL,
    messages_status BIGINT DEFAULT NULL,
    automod_status  BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS settings_permissions_roles
(
    guild_id     BIGINT,
    command_name VARCHAR(64),
    roles_ids    VARCHAR(255) DEFAULT '[]'
);