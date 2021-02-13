#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username reminderuser --dbname reminderdb <<-EOSQL
    DROP TABLE IF EXISTS "event";
    DROP TABLE IF EXISTS "log";
    DROP TABLE IF EXISTS "notification";
    DROP TABLE IF EXISTS "role";
    DROP TABLE IF EXISTS "user";
    DROP TABLE IF EXISTS "user_to_event";
    DROP TABLE IF EXISTS "apscheduler_jobs";

    CREATE TABLE "role" (
      "id" SERIAL NOT NULL,
      "name" VARCHAR(80),
      "description" VARCHAR(255),
      PRIMARY KEY("id"),
      UNIQUE ("name")
    );

    CREATE TABLE "user" (
      "id" SERIAL NOT NULL,
      "username" VARCHAR(40) NOT NULL,
      "password_hash" VARCHAR(128) NOT NULL,
      "email" VARCHAR(120) NOT NULL,
      "access_granted" BOOLEAN NOT NULL,
      "role_id" INT,
      "last_seen" TIMESTAMP,
      "creation_date" TIMESTAMP,
      "failed_login_attempts" INT,
      "pass_change_req" BOOLEAN,
      PRIMARY KEY("id"),
      UNIQUE ("username"),
      UNIQUE ("email"),
      FOREIGN KEY("role_id") REFERENCES "role"("id")
    );

    CREATE TABLE "event" (
      "id" SERIAL NOT NULL,
      "title" VARCHAR(100) NOT NULL,
      "details" VARCHAR(300),
      "time_creation" TIMESTAMP,
      "all_day_event" BOOLEAN NOT NULL,
      "time_event_start" TIMESTAMP,
      "time_event_stop" TIMESTAMP,
      "to_notify" BOOLEAN NOT NULL,
      "time_notify" TIMESTAMP,
      "author_uid" INT,
      "notification_sent" BOOLEAN,
      "is_active" BOOLEAN,
      PRIMARY KEY("id"),
      FOREIGN KEY("author_uid") REFERENCES "user"("id")
    );
    CREATE INDEX "ix_event_time_creation" ON "event" ("time_creation");
    CREATE INDEX "ix_event_time_event_start" ON "event" ("time_event_start");
    CREATE INDEX "ix_event_time_event_stop" ON "event" ("time_event_stop");
    CREATE INDEX "ix_event_time_notify" ON "event" ("time_notify");

    CREATE TABLE "log" (
      "id" SERIAL NOT NULL,
      "log_name" VARCHAR,
      "level" VARCHAR,
      "msg" VARCHAR(100),
      "time" TIMESTAMP,
      PRIMARY KEY("id")
    );

    CREATE TABLE "notification" (
      "id" SERIAL NOT NULL,
      "notify_unit" VARCHAR(10),
      "notify_interval" INT,
      PRIMARY KEY("id"),
      UNIQUE ("notify_unit")
    );

    CREATE TABLE "user_to_event" (
      "user_id" INT,
      "event_id" INT,
      FOREIGN KEY("user_id") REFERENCES "user"("id"),
      FOREIGN KEY("event_id") REFERENCES "event"("id")
    );

    -- Add user's roles
    INSERT INTO "role" ("name", "description")
    VALUES ('admin', 'Account with admin privileges'),
        ('user', 'Account dedicated for regular users');

    -- Add notification service settings
    INSERT INTO "notification" ("notify_unit", "notify_interval")
    VALUES ('hours',1);

    -- Add admin user to db
    -- Remember to add escape character \ before $ in password hash
    INSERT INTO "user" ("username", "password_hash", "email", "access_granted", "role_id", "last_seen", "creation_date", "failed_login_attempts", "pass_change_req")
    VALUES ('admin', 'pbkdf2:sha256:150000\$5zkkd2y1\$6b880d9f6b55a57c7d3bc5f90b18f16715e54dfb03355a3dda20b367e57cce1b', 'admin@niepodam.pl', True, '1', NULL, NOW()::timestamp, 0, False);
EOSQL