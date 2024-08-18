CREATE TABLE IF NOT EXISTS cards_main
(
    user_id BIGINT,
    rolls   INTEGER
);

CREATE TABLE IF NOT EXISTS cards_store
(
    id            BIGSERIAL,
    user_id       BIGINT,
    created_since INTEGER DEFAULT 0,
    card_id       INTEGER,
    rarity        VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS cards_trades
(
    id         BIGSERIAL,
    card_id    BIGINT,
    to_card_id BIGINT,
    created    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cards_timely
(
    user_id  BIGINT,
    next_get BIGINT
)