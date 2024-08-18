CREATE TABLE IF NOT EXISTS economy_main
(
    guild_id    BIGINT,
    user_id     BIGINT,
    money       BIGINT      DEFAULT 30,
    work        VARCHAR(64) DEFAULT NULL,
    works_count BIGINT      DEFAULT 0,
    in_game     BOOLEAN     DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS economy_bank
(
    guild_id BIGINT,
    user_id  BIGINT,
    amount   BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS economy_transactions
(
    guild_id    BIGINT,
    user_id     BIGINT,
    amount      BIGINT,
    type        varchar(24),
    description varchar(255)
);

CREATE TABLE IF NOT EXISTS economy_pets
(
    guild_id        BIGINT,
    user_id         BIGINT,
    pet             varchar(64),
    stamina_residue INTEGER DEFAULT 0,
    mana_residue    INTEGER DEFAULT 0,
    lvl             INTEGER DEFAULT 0,
    exp_now         INTEGER DEFAULT 0,
    exp_need        INTEGER DEFAULT 20,
    alert           INTEGER DEFAULT 0,
    in_fight        BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS economy_marry
(
    guild_id       BIGINT,
    marry_id       BIGSERIAL,
    user1_id       BIGINT,
    user2_id       BIGINT,
    balance        INT          DEFAULT 0,
    together_since INTEGER      DEFAULT 0,
    card_selected  VARCHAR(64)  DEFAULT 'love1',
    cards          VARCHAR(255) DEFAULT '["love1"]'
);

CREATE TABLE IF NOT EXISTS economy_shop
(
    guild_id    BIGINT,
    role_id     BIGINT,
    count       INTEGER      DEFAULT 0,
    unlimited   BOOLEAN      DEFAULT FALSE,
    description VARCHAR(255) DEFAULT NULL,
    cost        INTEGER
);

CREATE OR REPLACE FUNCTION check_mana_residue()
    RETURNS TRIGGER AS
$$
BEGIN
    IF NEW.mana_residue < 0 THEN
        DELETE
        FROM economy_pets
        WHERE guild_id = NEW.guild_id
          AND user_id = NEW.user_id
          AND pet = NEW.pet;
        RETURN NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER mana_residue_check
    BEFORE UPDATE
    ON economy_pets
    FOR EACH ROW
EXECUTE FUNCTION check_mana_residue();