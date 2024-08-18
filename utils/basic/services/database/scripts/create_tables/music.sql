CREATE TABLE IF NOT EXISTS music_last_listened
(
    user_id  BIGINT,
    encoded  VARCHAR(2048),
    listened INT
);


CREATE TABLE IF NOT EXISTS music_playlists
(
    name           VARCHAR(255) NOT NULL,
    uid            BIGSERIAL,
    user_id        BIGINT       NOT NULL,
    closed         BOOLEAN DEFAULT False,
    tracks         TEXT    DEFAULT '[]',
    listened_count BIGINT  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS music_tracks
(
    uid     BIGSERIAL,
    encoded VARCHAR(2048)
);


CREATE OR REPLACE FUNCTION music_last_trigger() RETURNS TRIGGER AS
$$
BEGIN
    IF (SELECT COUNT(*) FROM music_last_listened WHERE user_id = NEW.user_id) >= 10 THEN
        DELETE
        FROM music_last_listened
        WHERE ctid IN (SELECT ctid
                       FROM music_last_listened
                       WHERE user_id = NEW.user_id
                       ORDER BY listened
                       LIMIT 1);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION add_track_if_not_exists(enc VARCHAR(1024))
    RETURNS VOID AS
$$
BEGIN
    IF NOT EXISTS (SELECT uid FROM music_tracks WHERE encoded = enc) THEN
        INSERT INTO music_tracks(encoded) VALUES (enc);
    END IF;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER music_last_trigger
    BEFORE INSERT
    ON music_last_listened
    FOR EACH ROW
EXECUTE FUNCTION music_last_trigger();
