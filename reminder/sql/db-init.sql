CREATE TABLE event (
	id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	details VARCHAR(300), 
	time_creation DATETIME, 
	all_day_event BOOLEAN NOT NULL, 
	time_event_start DATETIME, 
	time_event_stop DATETIME, 
	to_notify BOOLEAN NOT NULL, 
	time_notify DATETIME, 
	author_uid INTEGER, 
	notification_sent BOOLEAN, 
	is_active BOOLEAN, 
	PRIMARY KEY (id), 
	CHECK (all_day_event IN (0, 1)), 
	CHECK (to_notify IN (0, 1)), 
	FOREIGN KEY(author_uid) REFERENCES user (id), 
	CHECK (notification_sent IN (0, 1)), 
	CHECK (is_active IN (0, 1))
)

CREATE TABLE log (
	id INTEGER NOT NULL, 
	log_name VARCHAR, 
	level VARCHAR, 
	msg VARCHAR(100), 
	time DATETIME, 
	PRIMARY KEY (id)
)

CREATE TABLE notification (
	id INTEGER NOT NULL, 
	notify_unit VARCHAR(10), 
	notify_interval INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (notify_unit)
)

CREATE TABLE role (
	id INTEGER NOT NULL, 
	name VARCHAR(80), 
	description VARCHAR(255), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(40) NOT NULL, 
	password_hash VARCHAR(128) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	access_granted BOOLEAN NOT NULL, 
	role_id INTEGER, 
	last_seen DATETIME, 
	creation_date DATETIME, 
	failed_login_attempts INTEGER, 
	pass_change_req BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email), 
	CHECK (access_granted IN (0, 1)), 
	FOREIGN KEY(role_id) REFERENCES role (id), 
	CHECK (pass_change_req IN (0, 1))
)

CREATE TABLE user_to_event (
	user_id INTEGER, 
	event_id INTEGER, 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	FOREIGN KEY(event_id) REFERENCES event (id)
)

CREATE INDEX ix_event_time_creation ON event (time_creation)
CREATE INDEX ix_event_time_event_start ON event (time_event_start)
CREATE INDEX ix_event_time_event_stop ON event (time_event_stop)
CREATE INDEX ix_event_time_notify ON event (time_notify)