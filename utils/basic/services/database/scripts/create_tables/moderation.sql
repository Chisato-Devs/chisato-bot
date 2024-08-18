CREATE TABLE IF NOT EXISTS moderation_global_warns
(
    guild_id     BIGINT,
    member_id    BIGINT,
    moderator_id BIGINT,
    warning_id   BIGINT,
    issue_time   INTEGER,
    reason       VARCHAR(256)
);

CREATE TABLE IF NOT EXISTS moderation_global_warns_settings
(
    guild_id        BIGINT,
    warnings_limit  INTEGER     DEFAULT 3,
    punishment_type VARCHAR(48) DEFAULT 'timeout',
    punishment_time VARCHAR(48) DEFAULT '1h'
);

CREATE TABLE IF NOT EXISTS moderation_global_bans
(
    guild_id     BIGINT,
    member_id    BIGINT,
    moderator_id BIGINT,
    reason       VARCHAR(256),
    unban_time   BIGINT
);

CREATE TABLE IF NOT EXISTS moderation_global_reports_settings
(
    guild_id   BIGINT,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS moderation_stats
(
    guild_id       BIGINT,
    member_id      BIGINT,
    bans_gived     INTEGER DEFAULT 0,
    warns_gived    INTEGER DEFAULT 0,
    timeouts_gived INTEGER DEFAULT 0,
    kicks_gived    INTEGER DEFAULT 0,
    bans_taked     INTEGER DEFAULT 0,
    warns_taked    INTEGER DEFAULT 0,
    timeouts_taked INTEGER DEFAULT 0,
    kick_taked     INTEGER DEFAULT 0
)
