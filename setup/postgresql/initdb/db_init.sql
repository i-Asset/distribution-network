-- CREATE DATABASE distributionnetworkdb WITH OWNER postgres;
-- USE distributionnetworkdb;


CREATE TABLE if not exists users (
    id integer NOT NULL PRIMARY KEY,
    first_name varchar(32) NOT NULL,
    sur_name varchar(32) NOT NULL,
    email varchar(64) NOT NULL,
    password varchar(256),
    bearer_token varchar(2048)
);

CREATE TABLE if not exists companies (
    id integer NOT NULL PRIMARY KEY,
    name varchar(64) NOT NULL,
    domain varchar(8),
    enterprise varchar(64),
    datetime timestamp with time zone,
    description text
);

CREATE TABLE if not exists is_admin_of_com (
    user_id integer NOT NULL REFERENCES users(id),
    company_id integer NOT NULL REFERENCES companies(id),
    creator_id integer REFERENCES users(id),
    datetime timestamp with time zone,
    PRIMARY KEY (user_id, company_id)
);

CREATE TABLE if not exists systems (
    name varchar(128) NOT NULL PRIMARY KEY,
    workcenter varchar(32),
    station varchar(32),
    kafka_servers varchar(1024),
    datetime timestamp with time zone,
    description text,
    company_id integer NOT NULL REFERENCES companies(id)
);

CREATE TABLE if not exists is_admin_of_sys (
    user_id integer NOT NULL REFERENCES users(id),
    system_name varchar(128) NOT NULL REFERENCES systems(name),
    creator_id integer REFERENCES users(id),
    datetime timestamp with time zone,
    PRIMARY KEY (user_id, system_name)
);

CREATE TABLE if not exists stream_apps (
    name varchar(64) NOT NULL,
    source_system varchar(128) NOT NULL REFERENCES systems(name),
    target_system varchar(128) NOT NULL REFERENCES systems(name),
    creator_id integer REFERENCES users(id),
    logic varchar(1024),
    status varchar(32),
    is_multi_source bool default false,
    datetime timestamp with time zone,
    description text,
    PRIMARY KEY (source_system, name)
);

CREATE TABLE if not exists aas (
    name varchar(64) NOT NULL,
    creator_id integer NOT NULL REFERENCES users(id),
    registry_uri varchar(256),
    datetime timestamp with time zone,
    description text,
    system_name varchar(128) NOT NULL REFERENCES systems(name),
    PRIMARY KEY (system_name, name)
);

CREATE TABLE if not exists mqtt_broker
(
    system_name varchar(128)     NOT NULL REFERENCES systems (name),
    server      varchar(1024) NOT NULL,
    version     varchar(32),
    topic       varchar(256)  NOT NULL,
    PRIMARY KEY (system_name)
);

CREATE TABLE if not exists client_apps (
    system_name varchar(128) NOT NULL REFERENCES systems(name),
    name varchar(64) NOT NULL,
    submodel_element_collection text,
    creator_id integer NOT NULL REFERENCES users(id),
    datetime timestamp with time zone,
    description text,
    on_kafka bool,
    key text,
    PRIMARY KEY (system_name, name)
);

CREATE TABLE if not exists datastreams
(
    system_name     varchar(128)   NOT NULL,
    client_name     varchar(64) NOT NULL,
    shortname      varchar(32)    NOT NULL,
    name            varchar(128),
    datastream_uri  text,
    description     text,
    aas_name        varchar(64),
    aas_system_name varchar(128),
    PRIMARY KEY (system_name, shortname),
    FOREIGN KEY (system_name, client_name) REFERENCES client_apps(system_name, name),
    FOREIGN KEY (aas_system_name, aas_name) REFERENCES aas(system_name, name)
);

CREATE TABLE if not exists subscriptions (
    system_name     varchar(128)   NOT NULL,
    client_name     varchar(64) NOT NULL,
    datastream_shortname  varchar(32)    NOT NULL,
    datastream_system       varchar(128)   NOT NULL,
    PRIMARY KEY (system_name, client_name, datastream_shortname),
    FOREIGN KEY (system_name, client_name) REFERENCES client_apps(system_name, name),
    FOREIGN KEY (datastream_system, datastream_shortname) REFERENCES datastreams(system_name, shortname)
);

-- ########################################################
-- ##################### Fill tables ######################
-- ########################################################

INSERT INTO users (id, first_name, sur_name, email, password) VALUES
(-1, 'Sue', 'Smith', 'sue.smith@example.com', md5('asdf')),
(-2, 'Stefan', 'Gunnarsson', 'stefan.gunnarsson@example.com', md5('asdf')),
(-3, 'Peter', 'Novak', 'peter.novak@example.com', md5('asdf')),
(-4, 'Anna', 'Gruber', 'anna.gruber@example.com', md5('asdf'));

INSERT INTO companies (id, name, domain, enterprise, datetime) VALUES
(-11, 'Icecars Inc.', 'cz', 'icecars', now()),
(-12, 'Iceland Gov', 'is', 'iceland', now()),
(-13, 'Datahouse Analytics GmbH', 'at', 'datahouse', now());

INSERT INTO is_admin_of_com (user_id, company_id, creator_id, datetime) VALUES
(-1, -11, -1, now()),
(-2, -12, -2, now()),
(-4, -13, -4, now());

INSERT INTO systems (name, workcenter, station, datetime, description, company_id) VALUES
('at.srfg.MachineFleet.Machine1', 'MachineFleet', 'Machine1', now(), 'Lorem Ipsum', -11),
('at.srfg.MachineFleet.Machine2', 'MachineFleet', 'Machine2', now(), 'Lorem Ipsum', -11),
('at.srfg.WeatherService.Stations', 'WeatherService', 'Stations', now(), 'Lorem Ipsum', -12),
('at.srfg.Analytics.MachineAnalytics', 'Analytics', 'MachineAnalytics', now(), 'Lorem Ipsum', -13);

INSERT INTO is_admin_of_sys (user_id, system_name, creator_id, datetime) VALUES
(-1, 'at.srfg.MachineFleet.Machine1', -1, now()),
(-3, 'at.srfg.MachineFleet.Machine1', -1, now()),
(-1, 'at.srfg.MachineFleet.Machine2', -1, now()),
(-3, 'at.srfg.MachineFleet.Machine2', -1, now()),
(-2, 'at.srfg.WeatherService.Stations', -2, now()),
(-4, 'at.srfg.Analytics.MachineAnalytics', -4, now());

INSERT INTO stream_apps (name, source_system, target_system, creator_id, logic, status, datetime, description) VALUES
('car1analytics', 'at.srfg.MachineFleet.Machine1', 'at.srfg.Analytics.MachineAnalytics', -1,
 'SELECT * FROM at.srfg.MachineFleet.Machine1;', 'init', now(), 'Lorem Ipsum'),
('car2analytics', 'at.srfg.MachineFleet.Machine2', 'at.srfg.Analytics.MachineAnalytics', -1,
 'SELECT * FROM at.srfg.MachineFleet.Machine2;', 'init', now(), 'Lorem Ipsum'),
('weather2car1', 'at.srfg.WeatherService.Stations', 'at.srfg.MachineFleet.Machine1', -2,
 'SELECT * FROM at.srfg.WeatherService.Stations;', 'init', now(), 'Lorem Ipsum'),
('weather2car2', 'at.srfg.WeatherService.Stations', 'at.srfg.Analytics.MachineAnalytics', -2,
 'SELECT * FROM at.srfg.WeatherService.Stations;', 'init', now(), 'Lorem Ipsum');

INSERT INTO client_apps (system_name, name, submodel_element_collection, creator_id, datetime, description, on_kafka, keyfile_av) VALUES
('at.srfg.MachineFleet.Machine1', 'machine_1', 'submodel_uri', -1, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.srfg.MachineFleet.Machine2', 'machine_2', 'submodel_uri', -1, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.srfg.WeatherService.Stations', 'weatherstation_1', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.srfg.WeatherService.Stations', 'weatherstation_2', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.srfg.WeatherService.Stations', 'weather_analytics', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.srfg.Analytics.MachineAnalytics','datastack-adapter', 'submodel_uri', -4, now(), 'Lorem Ipsum', TRUE, FALSE);

INSERT INTO aas (system_name, name, registry_uri, creator_id, datetime, description) VALUES
('at.srfg.MachineFleet.Machine1', 'machine', 'aas_registry.uri', -1, now(), 'Lorem Ipsum'),
('at.srfg.MachineFleet.Machine2', 'machine', 'aas_registry.uri', -1, now(), 'Lorem Ipsum'),
('at.srfg.WeatherService.Stations', 'weatherstation 1', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('at.srfg.WeatherService.Stations', 'weatherstation 2', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('at.srfg.WeatherService.Stations', 'weather_analytics', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('at.srfg.Analytics.MachineAnalytics','Datastack Adapter', 'aas_registry.uri', -4, now(), 'Lorem Ipsum');
