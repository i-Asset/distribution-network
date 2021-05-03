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
    name varchar(32) NOT NULL,
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
    name varchar(32) NOT NULL,
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
    client_name     varchar(32) NOT NULL,
    short_name      varchar(32)    NOT NULL,
    name            varchar(128),
    datastream_uri  text,
    description     text,
    aas_name        varchar(32),
    aas_system_name varchar(128),
    PRIMARY KEY (system_name, short_name),
    FOREIGN KEY (system_name, client_name) REFERENCES client_apps(system_name, name),
    FOREIGN KEY (aas_system_name, aas_name) REFERENCES aas(system_name, name)
);

CREATE TABLE if not exists subscriptions (
    system_name     varchar(128)   NOT NULL,
    client_name     varchar(32) NOT NULL,
    datastream_short_name   varchar(32)    NOT NULL,
    datastream_system       varchar(128)   NOT NULL,
    PRIMARY KEY (system_name, client_name, datastream_short_name),
    FOREIGN KEY (system_name, client_name) REFERENCES client_apps(system_name, name),
    FOREIGN KEY (datastream_system, datastream_short_name) REFERENCES datastreams(system_name, short_name)
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
('cz.icecars.iot4cps-wp5-CarFleet.Car1', 'iot4cps-wp5-CarFleet', 'Car1', now(), 'Lorem Ipsum', -11),
('cz.icecars.iot4cps-wp5-CarFleet.Car2', 'iot4cps-wp5-CarFleet', 'Car2', now(), 'Lorem Ipsum', -11),
('is.iceland.iot4cps-wp5-WeatherService.Stations', 'iot4cps-wp5-WeatherService', 'Stations', now(), 'Lorem Ipsum', -12),
('is.iceland.iot4cps-wp5-WeatherService.Services', 'iot4cps-wp5-WeatherService', 'Services', now(), 'Lorem Ipsum', -12),
('at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics', 'iot4cps-wp5-Analytics', 'RoadAnalytics', now(), 'Lorem Ipsum', -13);

INSERT INTO is_admin_of_sys (user_id, system_name, creator_id, datetime) VALUES
(-1, 'cz.icecars.iot4cps-wp5-CarFleet.Car1', -1, now()),
(-3, 'cz.icecars.iot4cps-wp5-CarFleet.Car1', -1, now()),
(-1, 'cz.icecars.iot4cps-wp5-CarFleet.Car2', -1, now()),
(-3, 'cz.icecars.iot4cps-wp5-CarFleet.Car2', -1, now()),
(-2, 'is.iceland.iot4cps-wp5-WeatherService.Stations', -2, now()),
(-2, 'is.iceland.iot4cps-wp5-WeatherService.Services', -2, now()),
(-4, 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics', -4, now());

INSERT INTO stream_apps (name, source_system, target_system, creator_id, logic, status, datetime, description) VALUES
('car1analytics', 'cz.icecars.iot4cps-wp5-CarFleet.Car1', 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics', -1,
 'SELECT * FROM cz.icecars.iot4cps-wp5-CarFleet.Car1;', 'init', now(), 'Lorem Ipsum'),
('car2analytics', 'cz.icecars.iot4cps-wp5-CarFleet.Car2', 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics', -1,
 'SELECT * FROM cz.icecars.iot4cps-wp5-CarFleet.Car2;', 'init', now(), 'Lorem Ipsum'),
('weather2car1', 'is.iceland.iot4cps-wp5-WeatherService.Stations', 'cz.icecars.iot4cps-wp5-CarFleet.Car1', -2,
 'SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations;', 'init', now(), 'Lorem Ipsum'),
('weather2car2', 'is.iceland.iot4cps-wp5-WeatherService.Stations', 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics', -2,
 'SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations;', 'init', now(), 'Lorem Ipsum');

INSERT INTO client_apps (system_name, name, submodel_element_collection, creator_id, datetime, description, on_kafka, keyfile_av) VALUES
('cz.icecars.iot4cps-wp5-CarFleet.Car1', 'car_1', 'submodel_uri', -1, now(), 'Lorem Ipsum', TRUE, FALSE),
('cz.icecars.iot4cps-wp5-CarFleet.Car2', 'car_2', 'submodel_uri', -1, now(), 'Lorem Ipsum', TRUE, FALSE),
('is.iceland.iot4cps-wp5-WeatherService.Stations', 'weatherstation_1', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('is.iceland.iot4cps-wp5-WeatherService.Stations', 'weatherstation_2', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('is.iceland.iot4cps-wp5-WeatherService.Services', 'forecast_service', 'submodel_uri', -2, now(), 'Lorem Ipsum', TRUE, FALSE),
('at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics','datastack-adapter', 'submodel_uri', -4, now(), 'Lorem Ipsum', TRUE, FALSE);

INSERT INTO aas (system_name, name, registry_uri, creator_id, datetime, description) VALUES
('cz.icecars.iot4cps-wp5-CarFleet.Car1', 'Car 1 AAS', 'aas_registry.uri', -1, now(), 'Lorem Ipsum'),
('cz.icecars.iot4cps-wp5-CarFleet.Car2', 'Car 2 AAS', 'aas_registry.uri', -1, now(), 'Lorem Ipsum'),
('is.iceland.iot4cps-wp5-WeatherService.Stations', 'Weatherstation 1', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('is.iceland.iot4cps-wp5-WeatherService.Stations', 'Weatherstation 2', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('is.iceland.iot4cps-wp5-WeatherService.Services', 'Forecast Service', 'aas_registry.uri', -2, now(), 'Lorem Ipsum'),
('at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics','Datastack Adapter', 'aas_registry.uri', -4, now(), 'Lorem Ipsum');
