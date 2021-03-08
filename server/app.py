import os
import sys

from dotenv import load_dotenv
from flask import Flask

# Import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__name__)), os.pardir)))
from server.create_database import create_tables, insert_samples_if_empty

from server.views.home import home_bp
from server.views.auth import auth
from server.views.company import company
from server.views.system import system
from server.views.client_apps import client_app
from server.views.stream_apps import stream_app
from server.views.aas import aas

# import api
from server.api.api_system import api_system
# from server.api.api_system import api_auth

# Import application-specific functions
from server.utils.kafka_interface import KafkaHandler, KafkaInterface


def create_app():
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
    # app.register_blueprint(api_auth)

    # load environment variables and start loggin
    app.config.from_envvar('APP_CONFIG_FILE')

    app.logger.setLevel(app.config["LOGLEVEL"])
    app.logger.info("Preparing the platform.")

    # TODO check the connection to postgres

    if app.config.get("KAFKA_BOOTSTRAP_SERVER"):
        # Create and add a Kafka instance to app. Recreate lost Kafka topics
        app.kafka_interface = KafkaInterface(app)
        app.kafka_interface.recreate_lost_topics()

        # Check the connection to Kafka exit if there isn't any
        if not app.kafka_interface.get_connection():
            app.logger.error("The connection to the Kafka Bootstrap Servers couldn't be established.")
            sys.exit(1)

        # Adding a KafkaHandler to the logger, ingests messages into kafka
        kh = KafkaHandler(app)
        app.logger.addHandler(kh)

    app.logger.info("Starting the platform.")

    # Creating the tables
    app.logger.info("Creating database distributionnetworkdb and insert sample data.")
    create_tables(app)
    if app.config.get("DB_INSERT_SAMPLE"):
        insert_samples_if_empty(app)

    if app.config.get("KAFKA_BOOTSTRAP_SERVER"):
        app.kafka_interface.create_default_topics()

    # # Test the Kafka Interface by creating and deleting a test topic
    # app.kafka_interface.create_system_topics("test.test.test.test")
    # app.kafka_interface.delete_system_topics("test.test.test.test")

    return app


if __name__ == '__main__':
    # Run application
    app = create_app()
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=1908)
