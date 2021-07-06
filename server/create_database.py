import logging
import os

import sqlalchemy as db
from dotenv import load_dotenv
from flask import Flask
# from .data import Articles
from passlib.hash import sha256_crypt

try:
    from server.utils.useful_functions import get_datetime, get_uid, is_logged_in
except ModuleNotFoundError:
    # This is needed
    from utils.useful_functions import get_datetime, get_uid, is_logged_in

# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')

DEFAULT_SYSTEMS = ["at.srfg.Analytics.MachineAnalytics",
                   "at.srfg.MachineFleet.Machine1",
                   "at.srfg.MachineFleet.Machine2",
                   "at.srfg.WeatherService.Stations"]

if app.config.get("DNET_SQLALCHEMY_DATABASE_DRIVER"):
    DNET_DB_URI = f'{app.config.get("DNET_SQLALCHEMY_DATABASE_DRIVER", "postgresql+psycopg2")}://'
    DNET_DB_URI += f'{app.config.get("POSTGRES_USER", "postgres")}:{app.config.get("POSTGRES_PASSWORD", "postgres")}'
    DNET_DB_URI += f'@{app.config.get("POSTGRES_HOST", "staging-main-db")}:{app.config.get("POSTGRES_PORT", 5432)}'
    DNET_DB_URI += f'/{app.config.get("DNET_SQLALCHEMY_DATABASE_NAME", "distributionnetworkdb")}'
else:
    DNET_DB_URI = f'{os.environ.get("DNET_SQLALCHEMY_DATABASE_DRIVER", "postgresql+psycopg2")}://'
    DNET_DB_URI += f'{os.environ.get("POSTGRES_USER", "postgres")}:{os.environ.get("POSTGRES_PASSWORD", "postgres")}'
    DNET_DB_URI += f'@{os.environ.get("POSTGRES_HOST", "staging-main-db")}:{os.environ.get("POSTGRES_PORT", 5432)}'
    DNET_DB_URI += f'/{os.environ.get("DNET_SQLALCHEMY_DATABASE_NAME", "distributionnetworkdb")}'
app.config.update({"SQLALCHEMY_DATABASE_URI": DNET_DB_URI})
app.logger.info("SQLALCHEMY_DATABASE_URI, update Postgres connection to " + app.config["SQLALCHEMY_DATABASE_URI"])


def check_postgres_connection(db_uri):
    succeeded = False
    try:
        engine = db.create_engine(db_uri)
        conn = engine.connect()
        result_proxy = conn.execute("SELECT 'ok';")
        app.logger.info(f"Connection to Postgres '{db_uri}' was established.")
        succeeded = True
        engine.dispose()
    except Exception as e:
        app.logger.info(f"Connection to Postgres '{db_uri}' could not be established: {e}")
    return succeeded


def drop_tables(app):
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
    DROP TABLE IF EXISTS mqtt_broker CASCADE;
    DROP TABLE IF EXISTS things CASCADE;
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
        db.Column('bearer_token', db.VARCHAR(2048), nullable=True)
    )
    app.config["tables"]["companies"] = db.Table(
        'companies', app.config['metadata'],
        db.Column('id', db.INTEGER, primary_key=True, unique=True),
        db.Column('name', db.VARCHAR(64), nullable=False),
        db.Column('domain', db.VARCHAR(8), nullable=False),
        db.Column('enterprise', db.VARCHAR(64), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True)
    )
    app.config["tables"]["systems"] = db.Table(
        'systems', app.config['metadata'],
        db.Column('name', db.VARCHAR(128), primary_key=True, unique=True),
        db.Column('workcenter', db.VARCHAR(32), nullable=False),
        db.Column('station', db.VARCHAR(32), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        db.Column('kafka_servers', db.VARCHAR(1024), nullable=True),
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
        db.Column('name', db.VARCHAR(64), primary_key=True),
        db.Column('source_system', db.ForeignKey('systems.name'), primary_key=True, nullable=False),
        db.Column('target_system', db.ForeignKey('systems.name'), nullable=False),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('logic', db.TEXT, nullable=True),
        db.Column('is_multi_source', db.BOOLEAN, nullable=False, default=False),
        db.Column('status', db.VARCHAR(32), nullable=False, default="init"),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True)
    )
    app.config["tables"]["things"] = db.Table(
        'things', app.config['metadata'],
        db.Column('name', db.VARCHAR(64), primary_key=True),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=True),
        db.Column('resource_uri', db.VARCHAR(256), nullable=True),
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
        db.Column('name', db.VARCHAR(64), primary_key=True),
        db.Column('resource_uri', db.VARCHAR(256), nullable=True),
        db.Column('creator_id', db.ForeignKey("users.id"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        db.Column('on_kafka', db.BOOLEAN, nullable=False, default=True),
        db.Column('key', db.TEXT, nullable=True)
    )
    app.config["tables"]["datastreams"] = db.Table(
        'datastreams', app.config['metadata'],
        db.Column('shortname', db.VARCHAR(32), primary_key=True),
        # construct a composite foreign key for client
        db.Column('client_name', db.VARCHAR(64), nullable=False),
        db.Column('system_name', db.VARCHAR(128), primary_key=True),
        db.ForeignKeyConstraint(('client_name', 'system_name'), ('client_apps.name', 'client_apps.system_name')),
        db.Column('name', db.VARCHAR(128)),
        db.Column('datastream_uri', db.VARCHAR(256), nullable=True),
        db.Column('description', db.TEXT, nullable=True),
        # construct a composite foreign key for thing
        db.Column('thing_name', db.VARCHAR(64), nullable=True),
        db.Column('thing_system_name', db.VARCHAR(128), nullable=True),
        db.ForeignKeyConstraint(('thing_name', 'thing_system_name'), ('things.name', 'things.system_name'))
    )
    app.config["tables"]["subscriptions"] = db.Table(
        'subscriptions', app.config['metadata'],
        # construct a composite foreign key for client
        db.Column('client_name', db.VARCHAR(64), nullable=False),
        db.Column('system_name', db.VARCHAR(128), primary_key=True),
        db.ForeignKeyConstraint(('client_name', 'system_name'), ('client_apps.name', 'client_apps.system_name')),

        db.Column('datastream_shortname', db.VARCHAR(32), primary_key=True),
        db.Column('datastream_system_name', db.VARCHAR(128)),
        db.ForeignKeyConstraint(('datastream_shortname', 'datastream_system_name'),
                                ('datastreams.shortname', 'datastreams.system_name'))
    )
    # Creates the tables
    app.config['metadata'].create_all(engine)
    engine.dispose()
    app.logger.info("Created tables.")


def insert_sample(app):
    default_password = "asdf"
    lorem_ipsum = """Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor."""
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
         'password': sha256_crypt.hash(default_password, salt=str(abs(id_sue)))},
        {'id': id_stefan,
         'first_name': 'Stefan',
         'sur_name': 'Gunnarsson',
         'email': 'stefan.gunnarsson@example.com',
         'password': sha256_crypt.hash(default_password, salt=str(abs(id_stefan)))},
        {'id': id_peter,
         'first_name': 'Peter',
         'sur_name': 'Novak',
         'email': 'peter.novak@example.com',
         'password': sha256_crypt.hash(default_password, salt=str(abs(id_peter)))},
        {'id': id_anna,
         'first_name': 'Anna',
         'sur_name': 'Gruber',
         'email': 'anna.gruber@example.com',
         'password': sha256_crypt.hash(default_password, salt=str(abs(id_anna)))}]
    ResultProxy = conn.execute(query, values_list)

    # Insert companies
    id_machine_comp = -11
    id_iceland = -12
    id_datahouse = -13
    query = db.insert(app.config["tables"]["companies"])
    values_list = [
        {'id': id_machine_comp,
         'name': 'Machine Inc.',
         'domain': 'at',
         'enterprise': 'srfg',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'id': id_iceland,
         'name': 'Iceland Gov',
         'domain': 'at',
         'enterprise': 'srfg',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'id': id_datahouse,
         'name': 'Datahouse Analytics GmbH',
         'domain': 'at',
         'enterprise': 'srfg',
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_com
    query = db.insert(app.config["tables"]["is_admin_of_com"])
    values_list = [
        {'user_id': id_sue,
         'company_id': id_machine_comp,
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
        {'name': 'at.srfg.MachineFleet.Machine1',
         'company_id': id_machine_comp,
         'workcenter': "MachineFleet",
         'station': "Machine",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'at.srfg.MachineFleet.Machine2',
         'company_id': id_machine_comp,
         'workcenter': "MachineFleet",
         'station': "Machine2",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'at.srfg.WeatherService.Stations',
         'company_id': id_iceland,
         'workcenter': "WeatherService",
         'station': "Stations",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'name': 'at.srfg.Analytics.MachineAnalytics',
         'company_id': id_datahouse,
         'workcenter': "Analytics",
         'station': "MachineAnalytics",
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_sys
    query = db.insert(app.config["tables"]["is_admin_of_sys"])
    values_list = [
        {'user_id': id_sue,
         'system_name': 'at.srfg.MachineFleet.Machine1',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_peter,
         'system_name': 'at.srfg.MachineFleet.Machine1',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_sue,
         'system_name': 'at.srfg.MachineFleet.Machine2',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_peter,
         'system_name': 'at.srfg.MachineFleet.Machine2',
         'creator_id': id_sue,
         'datetime': get_datetime()},
        {'user_id': id_stefan,
         'system_name': 'at.srfg.WeatherService.Stations',
         'creator_id': id_stefan,
         'datetime': get_datetime()},
        {'user_id': id_anna,
         'system_name': 'at.srfg.Analytics.MachineAnalytics',
         'creator_id': id_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert client
    query = db.insert(app.config["tables"]["client_apps"])
    values_list = [
        {'name': "machine",
         'system_name': "at.srfg.MachineFleet.Machine1",
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "machine",
         'system_name': "at.srfg.MachineFleet.Machine2",
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_1",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_2",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather_analytics",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "analytics",
         'system_name': 'at.srfg.Analytics.MachineAnalytics',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_anna,
         'datetime': get_datetime(),
         'description': lorem_ipsum}]
    ResultProxy = conn.execute(query, values_list)

    # Insert streams
    query = db.insert(app.config["tables"]["stream_apps"])
    values_list = [
        {'name': "machine1analytics",
         'source_system': "at.srfg.MachineFleet.Machine1",
         'target_system': "at.srfg.Analytics.MachineAnalytics",
         'logic': "SELECT * FROM at.srfg.MachineFleet.Machine1;",
         'creator_id': id_sue,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "machine2analytics",
         'source_system': "at.srfg.MachineFleet.Machine2",
         'target_system': "at.srfg.Analytics.MachineAnalytics",
         'logic': "SELECT * FROM at.srfg.MachineFleet.Machine2;",
         'creator_id': id_anna,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2machine1",
         'source_system': "at.srfg.WeatherService.Stations",
         'target_system': "at.srfg.MachineFleet.Machine1",
         'logic': "SELECT * FROM at.srfg.WeatherService.Stations;",
         'creator_id': id_stefan,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2analytics",
         'source_system': "at.srfg.WeatherService.Stations",
         'target_system': "at.srfg.Analytics.MachineAnalytics",
         'logic': "SELECT * FROM at.srfg.WeatherService.Stations;",
         'creator_id': id_stefan,
         'status': "init",
         'datetime': get_datetime(),
         'description': lorem_ipsum},]
    ResultProxy = conn.execute(query, values_list)

    # Insert Thing connection
    query = db.insert(app.config["tables"]["things"])
    values_list = [
        {'name': "machine",
         'system_name': "at.srfg.MachineFleet.Machine1",
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "machine",
         'system_name': "at.srfg.MachineFleet.Machine2",
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "Weatherstation_1",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "Weatherstation_2",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "Analytics-Software",
         'system_name': 'at.srfg.WeatherService.Stations',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "Datastack",
         'system_name': 'at.srfg.Analytics.MachineAnalytics',
         'resource_uri': "https://iasset.srfg.at/resources/resource_uri",
         'creator_id': id_anna,
         'datetime': get_datetime(),
         'description': lorem_ipsum}]
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
    drop_tables(app)

    # Creating the tables
    app.logger.info("Creating database distributionnetworkdb.")
    create_tables(app)

    # Insert sample for the demo scenario
    app.logger.info("Inserting sample data if the distributionnetworkdb is empty.")
    insert_samples_if_empty(app)

    app.logger.info("Finished.")
