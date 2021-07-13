import json
import os
import time
import zlib

import requests
import urllib
import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, jsonify

# Must be imported to use the app config
from flask import current_app as app
from passlib.hash import sha256_crypt

from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators, TextAreaField

from .api_auth import authorize_request, get_user_from_identity_service, get_user_id, get_party_from_identity_service
from ..utils.StreamAppHandler import stream_checks
from ..utils.useful_functions import get_datetime, is_logged_in, valid_level_name, encode_sys_url, decode_sys_url, \
    strip_dict, safe_strip, is_valid_level_name_string
from ..views.stream_apps import get_stream_payload, create_stream_app_from_payload, set_status_to

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_stream_app_controller = Blueprint("api_stream_app_controller", __name__)


@api_stream_app_controller.route(f"{prefix}/stream_app_statistic")
@api_stream_app_controller.route(f"{prefix}/stream_app_statistic/")
@api_stream_app_controller.route(f"{prefix}/stream_app_statistic/<string:any>")
@api_stream_app_controller.route(f"{prefix}/stream_app_statistic/<string:any>/")
def stream_stat_no_sys(any=None):
    return jsonify({"value": "Please specify an user id, system name, stream name and the desired statistic. Request methods: GET",
                    "url": f"{prefix}/stream_app_statistic/<string:user_id>/<string:system_url>/<string:stream_name>?<string:statistic='status'(default)|'is_running'|'stats'|'short_stats'|'logs_{{number_of_logs}}'|'config'", "status_code": 406}), 406

@api_stream_app_controller.route(f"{prefix}/stream_app_deploy")
@api_stream_app_controller.route(f"{prefix}/stream_app_deploy/")
@api_stream_app_controller.route(f"{prefix}/stream_app_deploy/<string:any>")
@api_stream_app_controller.route(f"{prefix}/stream_app_deploy/<string:any>/")
def stream_deploy_no_sys(any=None):
    return jsonify({"value": "Please specify an user id, system name and stream name. Request methods: POST, PUT",
                    "url": f"{prefix}/stream_app_deploy/<string:user_id>/<string:system_url>/<string:stream_name>", "status_code": 406}), 406

@api_stream_app_controller.route(f"{prefix}/stream_app_stop")
@api_stream_app_controller.route(f"{prefix}/stream_app_stop/")
@api_stream_app_controller.route(f"{prefix}/stream_app_stop/<string:any>")
@api_stream_app_controller.route(f"{prefix}/stream_app_stop/<string:any>/")
def stream_stop_no_sys(any=None):
    return jsonify({"value": "Please specify an user id, system name and stream name. Request methods: POST, PUT",
                    "url": f"{prefix}/stream_app_stop/<string:user_id>/<string:system_url>/<string:stream_name>", "status_code": 406}), 406


@api_stream_app_controller.route(f"{prefix}/stream_app_statistic/<string:user_id>/<string:system_url>/<string:stream_name>", methods=['GET'])
# @api_stream_app.route(f"{prefix}/stream_app_statistic/<string:user_id>/<string:system_url>/<string:stream_name>?<string:statistic='status'(default)|'is_running'|'stats'|'short_stats'|'logs_{{number_of_logs}}'|'config'", methods=['GET'])
def stream_statistic(user_id, system_url, stream_name):
    """
    Returns the statistic of a stream app in the distribution network of which the user is admin of and belong to the
    system. The following options are possible:
    'status'(default)|'is_running'|'stats'|'short_stats'|'logs_{{number_of_logs}}'|'config'
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param stream_name: name of the stream app
    :return: Json of the selected statistic
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/stream_app_statistic/<string:user_id>/<string:system_url>/<string:stream_name>?<string=statistic>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all streams that belong to the user with id user_id and system_name
    # cases without authorization are returned, here the user is definitely permitted to request the data
    system_name = decode_sys_url(system_url)
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(f"""
    SELECT count(*) FROM is_admin_of_sys AS iaos 
    WHERE iaos.user_id='{user_id}' AND iaos.system_name='{system_name}';""")
    iaos = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    if iaos[0].get("count", 0) == 0:
        engine.dispose()
        msg = f"The user '{user_id}' is not an admin of system '{system_name}' or it doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # 3) extract the desired statistic
    statistic = request.args.get('statistic', 'status')  # get the query string, status is default

    # 4) load the statistic and return the statistic
    payload = get_stream_payload(user_id, system_name, stream_name, api_call=True)
    if len(payload) == 0 or not isinstance(payload[0], dict):
        msg = f"The stream app '{stream_name}' within system '{system_name}' doesn't exist or you are not permitted."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # create the stream-app object
    stream_app = create_stream_app_from_payload(payload[0])

    if statistic == "status":
        response = stream_app.get_status()
        return jsonify({"stream app": stream_name, "statistic": "status", "value": response})
    if statistic == "is_running":
        response = stream_app.is_running()
        return jsonify({"stream app": stream_name, "statistic": "is_running", "value": response})
    if statistic == "stats":
        response = stream_app.get_stats()
        return jsonify({"stream app": stream_name, "statistic": "stats", "value": response})
    if statistic == "short_stats":
        response = stream_app.get_short_stats()
        return jsonify({"stream app": stream_name, "statistic": "short_stats", "value": response})
    if statistic == "config":
        response = stream_app.get_config()
        return jsonify({"stream app": stream_name, "statistic": "config", "value": response})

    if statistic.startswith("logs"):
        n_tail = None
        if statistic.count("_") == 1:
            try:
                n_tail = int(statistic.split("_")[-1])
            except:
                pass
        response = stream_app.get_logs(last_n=n_tail)
        return jsonify({"stream app": stream_name,
                        "statistic": "logs",
                        "value": [str(line.decode()) for line in response.splitlines()]})

    # not found, return error message
    return jsonify({"value": (f"the option 'statistic' is not recognized, choose one of. " +
                   "'status'(default)|'is_running'|'stats'|'short_stats'|'logs_{{number_of_logs}}'|'config'"),
                    "url": fct, "status_code": 406}), 406


@api_stream_app_controller.route(f"{prefix}/stream_app_deploy/<string:user_id>/<string:system_url>/<string:stream_name>", methods=['POST', 'PUT'])
def deploy_stream_app(user_id, system_url, stream_name):
    """
    Deploy a stream app by posting an empty message.
    :return: returns a json with the deployed stream_app and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/stream_apps_deploy/<string:user_id>/<string:system_url>/<string:stream_name>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the stream app exists
    # cases without authorization are returned, here the user is definitely permitted to request the data
    system_name = decode_sys_url(system_url)
    _ = request.json  # the request input is not needed
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(f"""
    SELECT count(*) FROM is_admin_of_sys AS iaos 
    WHERE iaos.user_id='{user_id}' AND iaos.system_name='{system_name}';""")
    iaos = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    if iaos[0].get("count", 0) == 0:
        engine.dispose()
        msg = f"The user '{user_id}' is not an admin of system '{system_name}' or it doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # 4) load the statistic and return
    payload = get_stream_payload(user_id, system_name, stream_name, api_call=True)
    if len(payload) == 0 or not isinstance(payload[0], dict):
        msg = f"The stream app '{stream_name}' within system '{system_name}' doesn't exist or you are not permitted."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403
    payload = payload[0]

    if not stream_checks.is_valid(payload, payload.get("is_multi_source")):
        msg = f"The stream app '{stream_name}' within system '{system_name}' is invalid."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # Check if the stream app can be deployed
    if request.method == "POST" and payload["status"] not in ["init", "idle"]:
        msg = f"The stream app '{stream_name}' can't be deployed when it already runs. Re-deploy with the PUT method."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # create the stream-app object
    stream_app = create_stream_app_from_payload(payload)

    # The stream can be started
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()

    if payload.get("is_multi_source"):  # start multi-source stream apps
        msg = "Multi-source stream-apps not implemented"
        app.logger.warning(msg)
        # app.logger.debug(f"Try to deploy multi-source stream app '{system_name}_{stream_name}'")
        # res = fab_streams.local_deploy_multi(system_name=system_name, stream_name=stream_name,
        #                                      stream=stream, logger=app.logger)
        # if len(res) != 64:  # res is the UUID of the container
        #     app.logger.warning(
        #         f"'{fab_streams.build_name(system_name, stream_name)}' was deployed with response {res}.")
        # app.logger.debug(f"Deployed multi-source stream '{system_name}_{stream_name}'.")

    else:  # for single source stream apps
        app.logger.debug(f"Try to deploy single-source stream app '{stream_app.get_name()}'")
        if stream_app.is_running():
            stream_app.stop()
            time.sleep(1)
        stream_app.deploy()
        msg = f"The stream-app '{stream_app.get_name()}' has been deployed."

    # Set status in DB
    set_status_to(system_name, stream_name, "starting")
    transaction.commit()

    app.logger.info(msg)
    return jsonify({"value": msg, "url": fct, "status_code": 200}), 200


@api_stream_app_controller.route(f"{prefix}/stream_app_stop/<string:user_id>/<string:system_url>/<string:stream_name>", methods=['POST'])
def stop_stream_app(user_id, system_url, stream_name):
    """
    Stop a stream app by posting an empty message.
    :return: returns a json with the deployed stream_app and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/stream_apps_stop/<string:user_id>/<string:system_url>/<string:stream_name>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the stream app exists
    # cases without authorization are returned, here the user is definitely permitted to request the data
    system_name = decode_sys_url(system_url)
    _ = request.json  # the request input is not needed
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(f"""
    SELECT count(*) FROM is_admin_of_sys AS iaos 
    WHERE iaos.user_id='{user_id}' AND iaos.system_name='{system_name}';""")
    iaos = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    if iaos[0].get("count", 0) == 0:
        engine.dispose()
        msg = f"The user '{user_id}' is not an admin of system '{system_name}' or it doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # 4) load the statistic and return
    payload = get_stream_payload(user_id, system_name, stream_name, api_call=True)
    if len(payload) == 0 or not isinstance(payload[0], dict):
        msg = f"The stream app '{stream_name}' within system '{system_name}' doesn't exist or you are not permitted."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403
    payload = payload[0]

    if not stream_checks.is_valid(payload, payload.get("is_multi_source")):
        msg = f"The stream app '{stream_name}' within system '{system_name}' is invalid."
        app.logger.warning(f"{fct}: {msg}, payload: '{payload}'")
        return jsonify({"value": msg, "url": fct, "status_code": 403}), 403

    # create the stream-app object
    stream_app = create_stream_app_from_payload(payload)

    # The stream can be started
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()

    if payload.get("is_multi_source"):  # start multi-source stream apps
        msg = "Multi-source stream-apps not implemented"
        app.logger.warning(msg)
        # app.logger.debug(f"Try to deploy multi-source stream app '{system_name}_{stream_name}'")
        # res = fab_streams.local_deploy_multi(system_name=system_name, stream_name=stream_name,
        #                                      stream=stream, logger=app.logger)
        # if len(res) != 64:  # res is the UUID of the container
        #     app.logger.warning(
        #         f"'{fab_streams.build_name(system_name, stream_name)}' was deployed with response {res}.")
        # app.logger.debug(f"Deployed multi-source stream '{system_name}_{stream_name}'.")

    else:  # for single source stream apps
        app.logger.debug(f"Stopping the single-source stream app '{stream_app.get_name()}'")
        stream_app.stop()
        msg = f"The stream-app '{stream_app.get_name()}' has been stopped."

    # Set status in DB
    set_status_to(system_name, stream_name, "stopped")
    transaction.commit()

    app.logger.info(msg)
    return jsonify({"value": msg, "url": fct, "status_code": 200}), 200
