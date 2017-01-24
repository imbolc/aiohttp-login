-- case independent text field
CREATE EXTENSION IF NOT EXISTS citext;

-- users
DROP TYPE IF EXISTS user_status CASCADE;
CREATE TYPE user_status AS ENUM (
    'confirmation', 'active', 'banned');

DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    id              serial PRIMARY KEY,
    name            text NOT NULL,
    email           citext NOT NULL UNIQUE,
    password        text NOT NULL,
    status          user_status NOT NULL,
    created_at      timestamp NOT NULL,
    created_ip      text NOT NULL,
    vkontakte       text UNIQUE,
    google          text UNIQUE,
    facebook        text UNIQUE
);


-- confirmations
DROP TYPE IF EXISTS confirmation_action CASCADE;
CREATE TYPE confirmation_action AS ENUM (
    'registration', 'reset_password', 'change_email');

DROP TABLE IF EXISTS confirmations CASCADE;
CREATE TABLE confirmations (
    code            text PRIMARY KEY,
    user_id         int REFERENCES users(id),
    action          confirmation_action NOT NULL,
    data            text,
    created_at      timestamp NOT NULL
);
CREATE UNIQUE INDEX ON confirmations (user_id, action);
