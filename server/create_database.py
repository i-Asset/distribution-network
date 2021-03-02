import logging

import sqlalchemy as db
from dotenv import load_dotenv
from flask import Flask
# from .data import Articles
from passlib.hash import sha256_crypt

try:
    from server.views.useful_functions import get_datetime, get_uid, is_logged_in
except ModuleNotFoundError:
    # This is needed
    from views.useful_functions import get_datetime, get_uid, is_logged_in

# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')


def drop_tables():
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS companies CASCADE;
    DROP TABLE IF EXISTS systems CASCADE;
    DROP TABLE IF EXISTS is_admin_of_com CASCADE;
    DROP TABLE IF EXISTS is_admin_of_sys CASCADE;
    DROP TABLE IF EXISTS client_apps CASCADE;
    DROP TABLE IF EXISTS stream_apps CASCADE;
    DROP TABLE IF EXISTS aas CASCADE;
    DROP TABLE IF EXISTS mqtt_broker CASCADE;
    DROP TABLE IF EXISTS datastreams CASCADE;
    DROP TABLE IF EXISTS subscriptions CASCADE;
    """
    result_proxy = conn.execute(query)
    engine.dispose()


def create_tables(app):
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()
    app.config['metadata'] = db.MetaData()

    # Define all entities and relations
    app.config["tables"] = dict()
    app.config["tables"]["users"] = db.Table(
        'users', app.config['metadata'],
        db.Column('id', db.INTEGER, primary_key=True, unique=True),
        db.Column('first_name', db.VARCHAR(32), nullable=False),
        db.Column('sur_name', db.VARCHAR(32), nullable=False),
        db.Column('email', db.VARCHAR(64), nullable=False, unique=True),
        db.Column('password', db.VARCHAR(256), nullable=True),
        db.Column('bearer_token', db.VARCHAR(256), nullable=True)
    )
    app.config["tables"]["companies"] = db.Table(
        'companies', app.config['metadata'],
        db.Column('id', db.INTEGER, primary_key=True, unique=True),
        db.Column('name', db.VARCHAR(64), nullable=False),
        db.Column('domain', db.CHAR(8), nullable=False),
        db.Column('enterprise', db.CHAR(64), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True)
    )
    app.config["tables"]["systems"] = db.Table(
        'systems', app.config['metadata'],
        db.Column('name', db.CHAR(128), primary_key=True, unique=True),
        db.Column('workcenter', db.CHAR(32), nullable=False),
        db.Column('station', db.CHAR(32), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        db.Column('company_id', db.ForeignKey('companies.id'), nullable=False)
    )
    app.config["tables"]["is_admin_of_com"] = db.Table(
        'is_admin_of_com', app.config['metadata'],
        db.Column('user_id', db.ForeignKey("users.id"), primary_key=True, nullable=False),
        db.Column('company_id', db.ForeignKey('companies.id'), primary_key=True, nullable=False),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["is_admin_of_sys"] = db.Table(
        'is_admin_of_sys', app.config['metadata'],
        db.Column('user_id', db.ForeignKey("users.id"), primary_key=True, nullable=False),
        db.Column('system_name', db.ForeignKey('systems.name'), primary_key=True, nullable=False),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["stream_apps"] = db.Table(
        'stream_apps', app.config['metadata'],
        db.Column('name', db.VARCHAR(32), primary_key=True),
        db.Column('source_system', db.ForeignKey('systems.name'), primary_key=True, nullable=False),
        db.Column('target_system', db.ForeignKey('systems.name'), nullable=False),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('logic', db.VARCHAR(1024), nullable=True),
        db.Column('status', db.VARCHAR(32), nullable=False, default="init"),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True)
    )
    app.config["tables"]["aas"] = db.Table(
        'aas', app.config['metadata'],
        db.Column('name', db.VARCHAR(64), primary_key=True),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('registry_uri', db.VARCHAR(256), nullable=True),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        db.Column('system_name', db.ForeignKey('systems.name'), primary_key=True)
    )
    app.config["tables"]["mqtt_broker"] = db.Table(
        'mqtt_broker', app.config['metadata'],
        db.Column('system_name', db.ForeignKey('systems.name'), primary_key=True),
        db.Column('server', db.VARCHAR(1024), nullable=False),
        db.Column('version', db.VARCHAR(32), nullable=True),
        db.Column('topic', db.VARCHAR(1024), nullable=False)
    )
    app.config["tables"]["client_apps"] = db.Table(
        'client_apps', app.config['metadata'],
        db.Column('system_name', db.ForeignKey('systems.name'), primary_key=True),
        db.Column('name', db.VARCHAR(32), primary_key=True),
        db.Column('submodel_element_collection', db.TEXT, nullable=True),
        db.Column('aas_uri', db.VARCHAR(256), nullable=True),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        db.Column('on_kafka', db.BOOLEAN, nullable=False, default=True),
        db.Column('key', db.TEXT, nullable=True)
    )
    app.config["tables"]["datastreams"] = db.Table(
        'datastreams', app.config['metadata'],
        db.Column('short_name', db.VARCHAR(32), primary_key=True),
        # construct a composite foreign key for client
        db.Column('client_name', db.VARCHAR(32), nullable=False),
        db.Column('system_name', db.CHAR(128), primary_key=True),
        db.ForeignKeyConstraint(['client_name', 'system_name'], ['client_apps.name', 'client_apps.system_name']),
        db.Column('name', db.VARCHAR(128)),
        db.Column('datastream_uri', db.VARCHAR(256), nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        # construct a composite foreign key for aas
        db.Column('aas_name', db.VARCHAR(64), nullable=True),
        db.Column('aas_system_name', db.CHAR(128), nullable=True),
        db.ForeignKeyConstraint(['aas_name', 'aas_system_name'], ['aas.name', 'aas.system_name'])
    )
    app.config["tables"]["subscriptions"] = db.Table(
        'subscriptions', app.config['metadata'],
        # construct a composite foreign key for client
        db.Column('client_name', db.VARCHAR(32), nullable=False),
        db.Column('system_name', db.CHAR(128), primary_key=True),
        db.ForeignKeyConstraint(['client_name', 'system_name'], ['client_apps.name', 'client_apps.system_name']),

        db.Column('datastream_short_name', db.VARCHAR(32), primary_key=True),
        db.Column('datastream_system_name', db.CHAR(128)),
        db.ForeignKeyConstraint(['datastream_short_name', 'datastream_system_name'],
                                ['datastreams.short_name', 'datastreams.system_name'])
    )
    # Creates the tables
    app.config['metadata'].create_all(engine)
    engine.dispose()
    app.logger.info("Created tables.")


def insert_sample(app):
    default_password = "asdf"
    lorem_ipsum = """Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. 
    Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec 
    quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim."""
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    # # Drop Tables before ingestions
    # for tbl in reversed(app.config['metadata'].sorted_tables):
    #     engine.execute(tbl.delete())

    # Inserting many records at ones in users
    id_sue = -1
    id_stefan = -2
    id_peter = -3
    id_anna = -4
    query = db.insert(app.config["tables"]["users"])
    values_list = [
        {'id': id_sue,
         'first_name': 'Sue',
         'sur_name': 'Smith',
         'email': 'sue.smith@example.com',
         'password': sha256_crypt.hash(default_password)},
        {'id': id_stefan,
         'first_name': 'Stefan',
         'sur_name': 'Gunnarsson',
         'email': 'stefan.gunnarsson@example.com',
         'password': sha256_crypt.hash(default_password)},
        {'id': id_peter,
         'first_name': 'Peter',
         'sur_name': 'Novak',
         'email': 'peter.novak@example.com',
         'password': sha256_crypt.hash(default_password)},
        {'id': id_anna,
         'first_name': 'Anna',
         'sur_name': 'Gruber',
         'email': 'anna.gruber@example.com',
         'password': sha256_crypt.hash(default_password)}]
    ResultProxy = conn.execute(query, values_list)

    # Insert companies
    id_icecars = -11
    id_iceland = -12
    id_datahouse = -13
    query = db.insert(app.config["tables"]["companies"])
    values_list = [
        {'id': id_icecars,
         'name': 'Icecars Inc.',
         'domain': 'cz',
         'enterprise': 'icecars',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'id': id_iceland,
         'name': 'Iceland Gov',
         'domain': 'is',
         'enterprise': 'iceland',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'id': id_datahouse,
         'name': 'Datahouse Analytics GmbH',
         'domain': 'at',
         'enterprise': 'datahouse',
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_com
    query = db.insert(app.config["tables"]["is_admin_of_com"])
    values_list = [
        {'user_id': id_sue,
         'company_id': id_icecars,
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_stefan,
         'company_id': id_iceland,
         'creator_id': id_stefan,
         'datetime': get_datetime()},
        {'user_id': id_anna,
         'company_id': id_datahouse,
         'creator_id': id_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert systems
    query = db.insert(app.config["tables"]["systems"])
    values_list = [
        {'name': 'cz.icecars.iot4cps-wp5-CarFleet.Car1',
         'company_id': id_icecars,
         'workcenter': "iot4cps-wp5-CarFleet",
         'station': "Car1",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'cz.icecars.iot4cps-wp5-CarFleet.Car2',
         'company_id': id_icecars,
         'workcenter': "iot4cps-wp5-CarFleet",
         'station': "Car2",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'is.iceland.iot4cps-wp5-WeatherService.Stations',
         'company_id': id_iceland,
         'workcenter': "iot4cps-wp5-WeatherService",
         'station': "Stations",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'is.iceland.iot4cps-wp5-WeatherService.Services',
         'company_id': id_iceland,
         'workcenter': "iot4cps-wp5-WeatherService",
         'station': "Services",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics',
         'company_id': id_datahouse,
         'workcenter': "iot4cps-wp5-Analytics",
         'station': "RoadAnalytics",
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_sys
    query = db.insert(app.config["tables"]["is_admin_of_sys"])
    values_list = [
        {'user_id': id_sue,
         'system_name': 'cz.icecars.iot4cps-wp5-CarFleet.Car1',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_peter,
         'system_name': 'cz.icecars.iot4cps-wp5-CarFleet.Car1',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_sue,
         'system_name': 'cz.icecars.iot4cps-wp5-CarFleet.Car2',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_peter,
         'system_name': 'cz.icecars.iot4cps-wp5-CarFleet.Car2',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_stefan,
         'system_name': 'is.iceland.iot4cps-wp5-WeatherService.Stations',
         'creator_id': id_stefan,
         'datetime': get_datetime()},
        {'user_id': id_stefan,
         'system_name': 'is.iceland.iot4cps-wp5-WeatherService.Services',
         'creator_id': id_stefan,
         'datetime': get_datetime()},
        {'user_id': id_anna,
         'system_name': 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics',
         'creator_id': id_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert client
    query = db.insert(app.config["tables"]["client_apps"])
    values_list = [
        {'name': "car_1",
         'system_name': "cz.icecars.iot4cps-wp5-CarFleet.Car1",
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "car_2",
         'system_name': "cz.icecars.iot4cps-wp5-CarFleet.Car2",
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_1",
         'system_name': 'is.iceland.iot4cps-wp5-WeatherService.Stations',
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_2",
         'system_name': 'is.iceland.iot4cps-wp5-WeatherService.Stations',
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "forecast_service",
         'system_name': 'is.iceland.iot4cps-wp5-WeatherService.Services',
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "datastack-adapter",
         'system_name': 'at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics',
         'submodel_element_collection': "submodel_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum}]
    ResultProxy = conn.execute(query, values_list)

    # Insert streams
    query = db.insert(app.config["tables"]["stream_apps"])
    values_list = [
        {'name': "car1analytics",
         'source_system': "cz.icecars.iot4cps-wp5-CarFleet.Car1",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'logic': "SELECT * FROM cz.icecars.iot4cps-wp5-CarFleet.Car1;",
         'creator_id': id_sue,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "car2analytics",
         'source_system': "cz.icecars.iot4cps-wp5-CarFleet.Car2",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'logic': "SELECT * FROM cz.icecars.iot4cps-wp5-CarFleet.Car1;",
         'creator_id': id_sue,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2car1",
         'source_system': "is.iceland.iot4cps-wp5-WeatherService.Stations",
         'target_system': "cz.icecars.iot4cps-wp5-CarFleet.Car1",
         'logic': "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations;",
         'creator_id': id_stefan,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2analytics",
         'source_system': "is.iceland.iot4cps-wp5-WeatherService.Stations",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'logic': "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations;",
         'creator_id': id_stefan,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},]
    ResultProxy = conn.execute(query, values_list)

    engine.dispose()
    app.logger.info("Ingested data into tables.")


def insert_samples_if_empty(app):
    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = "SELECT count(*) FROM users;"
    result_proxy = conn.execute(query)
    users = [dict(c.items()) for c in result_proxy.fetchall()]

    query = "SELECT count(*) FROM companies;"
    result_proxy = conn.execute(query)
    companies = [dict(c.items()) for c in result_proxy.fetchall()]

    query = "SELECT count(*) FROM systems;"
    result_proxy = conn.execute(query)
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    engine.dispose()

    if users[0]["count"] + companies[0]["count"] + systems[0]["count"] == 0:
        app.logger.info("The distributionnetworkdb is empty, insert samples into distributionnetworkdb.")
        insert_sample(app)


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)

    # Creating the tables
    app.logger.info("Drop database distributionnetworkdb.")
    drop_tables()

    # Creating the tables
    app.logger.info("Creating database distributionnetworkdb.")
    create_tables(app)

    # Insert sample for the demo scenario
    app.logger.info("Inserting sample data if the distributionnetworkdb is empty.")
    insert_samples_if_empty(app)

    app.logger.info("Finished.")
