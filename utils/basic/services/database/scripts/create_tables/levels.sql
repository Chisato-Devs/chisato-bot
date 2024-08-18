CREATE TABLE IF NOT EXISTS levels_main
(
    guild_id BIGINT,
    user_id  BIGINT,
    prestige INTEGER DEFAULT 0,
    level    INTEGER DEFAULT 1,
    exp_need BIGINT  DEFAULT 30,
    exp_now  BIGINT  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS levels_settings
(
    guild_id   BIGINT,
    alert      BOOLEAN       DEFAULT TRUE,
    status     BOOLEAN       DEFAULT TRUE,
    embed_data VARCHAR(4096) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS levels_prestige_rewards
(
    guild_id    BIGINT,
    prestige_id INTEGER,
    role_id     BIGINT
);