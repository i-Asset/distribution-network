import json
import os
import sys
import time

import requests
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__name__)), os.pardir)))
from server.create_database import check_postgres_connection, create_tables, insert_samples_if_empty

from server.views.home import home_bp
from server.views.auth import auth
from server.views.company import company
from server.views.system import system
from server.views.client_apps import client_app
from server.views.stream_apps import stream_app
from server.views.aas import aas

# import api
from server.api.api_system import api_system
from server.api.api_stream_app import api_stream_app
from server.api.api_client_app import api_client_app
from server.api.api_aas_connection import api_aas
from server.api.api_datastreams import api_datastreams
from server.api.api_auth import check_iasset_connection

# Import application-specific functions
from server.utils.kafka_interface import KafkaHandler, KafkaInterface
from server.utils.StreamAppHandler.stream_app_handler import create_client


def create_app():
    ########################################################
    # ################# register modules ################# #
    ########################################################

    # load environment variables automatically from a .env file in the same directory
    load_dotenv()

    # Create Flask app and load configs
    app = Flask(__name__)

    # Register modules as blueprint
    app.register_blueprint(home_bp)
    app.register_blueprint(auth)
    app.register_blueprint(company)
    app.register_blueprint(system)
    app.register_blueprint(client_app)
    app.register_blueprint(stream_app)
    app.register_blueprint(aas)

    # Register api as blueprint
    app.register_blueprint(api_system)
    app.register_blueprint(api_stream_app)
    app.register_blueprint(api_client_app)
    app.register_blueprint(api_aas)
    app.register_blueprint(api_datastreams)

    ########################################################
    # ########### load and update env variables ########## #
    ########################################################

    # load environment variables
    app.config.from_envvar('APP_CONFIG_FILE')

    app.logger.setLevel(app.config["LOGLEVEL"])
    app.logger.info("Preparing the platform.")

    with open("utils/country_codes.json") as f:
        codes = json.loads(f.read())
        app.config["COUNTRY_CODES"] = {v["name"]: k for k,v in codes.items() if not k.startswith("__")}

    if os.environ.get("DNET_STARTUP_TIME"):
        app.config.update({"DNET_STARTUP_TIME": os.environ.get("DNET_STARTUP_TIME")})
        app.logger.info("Update DNET_STARTUP_TIME to " + app.config["DNET_STARTUP_TIME"])

    if os.environ.get("DNET_IDENTITY_SERVICE"):
        app.config.update({"DNET_IDENTITY_SERVICE": os.environ.get("DNET_IDENTITY_SERVICE")})
        app.logger.info("Update i-Asset connection to " + app.config["DNET_IASSET_SERVER"])
    else:
        app.logger.info("DNET_IDENTITY_SERVICE not in the compose-environment variables, keep {}".format(app.config.get(
            "DNET_IDENTITY_SERVICE", None)))

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

    if os.environ.get("DNET_KAFKA_BOOTSTRAP_SERVER"):
        app.config.update({"DNET_KAFKA_BOOTSTRAP_SERVER": os.environ.get("DNET_KAFKA_BOOTSTRAP_SERVER"),
                           "KAFKA_BOOTSTRAP_SERVER": os.environ.get("DNET_KAFKA_BOOTSTRAP_SERVER")})
        app.logger.info("Update Kafka Bootstrap servers to " + app.config["DNET_KAFKA_BOOTSTRAP_SERVER"])
    else:
        app.config.update({"KAFKA_BOOTSTRAP_SERVER": app.config.get("DNET_KAFKA_BOOTSTRAP_SERVER")})
        app.logger.info("DNET_KAFKA_BOOTSTRAP_SERVER not in the compose-environment variables, keep {}".format(app.config.get(
            "DNET_KAFKA_BOOTSTRAP_SERVER", None)))

    # wait for infrastructure services
    if app.config.get("DNET_STARTUP_TIME"):
        app.logger.info(f"Waiting {app.config.get('DNET_STARTUP_TIME')} s for other services.")
        time.sleep(float(app.config.get("DNET_STARTUP_TIME")))

    ########################################################
    # ############## test i-asset connection ############# #
    ########################################################

    if not check_iasset_connection(asset_uri=app.config["DNET_IDENTITY_SERVICE"]):
        app.logger.error("The connection to i-Asset server couldn't be established.")
        sys.exit(1)

    ########################################################
    # ############ test connection and feed db ########### #
    ########################################################

    if not check_postgres_connection(db_uri=app.config["SQLALCHEMY_DATABASE_URI"]):
        app.logger.error("The connection to Postgres couldn't be established.")
        sys.exit(2)

    # Creating the tables
    app.logger.info("Creating database distributionnetworkdb and insert sample data.")
    create_tables(app)
    if app.config.get("DB_INSERT_SAMPLE"):
        insert_samples_if_empty(app)

    ########################################################
    # ###### # test connection and recreate kafka ######## #
    ########################################################

    if app.config.get("KAFKA_BOOTSTRAP_SERVER"):
        # Create and add a Kafka instance to app
        app.kafka_interface = KafkaInterface(app)

        # Check the connection to Kafka exit if there isn't any
        if not app.kafka_interface.get_connection():
            app.logger.error("The connection to the Kafka Bootstrap Servers couldn't be established.")
            sys.exit(3)

        # Recreate lost Kafka topics
        app.kafka_interface.recreate_lost_topics()

        # # Test the Kafka Interface by creating and deleting a test topic
        # app.kafka_interface.create_system_topics("test.test.test.test")
        # app.kafka_interface.delete_system_topics("test.test.test.test")

        # Adding a KafkaHandler to the logger, ingests messages into kafka
        kh = KafkaHandler(app)
        app.logger.addHandler(kh)

    ########################################################
    # ########### rebuild the stream-app image #############
    ########################################################

    app.logger.info("docker-py: Re-build the streamhub_stream-app image.")
    client = create_client()
    client.images.build(path="streamhub/StreamHub", dockerfile="Dockerfile", tag="streamhub_stream-app", rm=True)

    ########################################################
    # ################ register swagger ui ################ #
    ########################################################

    swagger_url = '/distributionnetwork/swagger-ui.html'

    # Register the Swagger ui as blueprint
    @app.route(f"{swagger_url}/api")
    @app.route(f"/{swagger_url}/api/<path:path>")
    def send_api(path):
        return send_from_directory("api", path)

    api_url = 'api/swagger.yaml'
    swaggerui_blueprint = get_swaggerui_blueprint(swagger_url, api_url,
                                                  config={'app_name': "Swagger UI Distribution Network"})
    app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

    app.logger.info("Starting the platform.")
    return app


if __name__ == '__main__':
    # Run application
    app = create_app()
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=1908)
