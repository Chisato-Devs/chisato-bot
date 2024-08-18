CREATE TABLE IF NOT EXISTS rooms_users_setting
(
    guild_id
    BIGINT,
    user_id
    BIGINT,
    room_name
    VARCHAR
(
    255
),
    limit_users INTEGER DEFAULT 2
    );

CREATE TABLE IF NOT EXISTS rooms_temp_data
(
    guild_id
    BIGINT,
    voice_id
    BIGINT,
    leader
    BIGINT,
    requests
    INTEGER
    DEFAULT
    0,
    requests_time
    INTEGER,
    is_love
    BOOLEAN
    DEFAULT
    FALSE
);

CREATE TABLE IF NOT EXISTS rooms_guild_settings
(
    guild_id
    BIGINT,
    category
    BIGINT,
    founder
    BIGINT,
    message_id
    BIGINT,
    channel
    BIGINT,
    love_room
    BIGINT
);
