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
from ..utils.useful_functions import get_datetime, is_logged_in, valid_level_name, encode_sys_url, decode_sys_url, \
    strip_dict, safe_strip, is_valid_level_name_string

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_stream_app = Blueprint("api_stream_app", __name__)


@api_stream_app.route(f"{prefix}/stream_apps")
@api_stream_app.route(f"{prefix}/stream_apps/")
@api_stream_app.route(f"{prefix}/stream_apps/<string:any>")
@api_stream_app.route(f"{prefix}/stream_apps/<string:any>/")
def streams_no_sys(any=None):
    return jsonify({"value": "Please specify an user id and a system name.",
                    "url": f"{prefix}/stream_apps/<string:user_id>/<string:system_name>", "status_code": 406}), 406


@api_stream_app.route(f"{prefix}/stream_apps/<string:user_id>/<string:system_url>", methods=['GET'])
@api_stream_app.route(f"{prefix}/stream_apps/<string:user_id>/<string:system_url>/", methods=['GET'])
def streams_per_system(user_id, system_url):
    """
    Searches for all stream apps in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found stream apps
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/stream_apps/<string:user_id>/<string:system_url>"
    user_id = get_user_id(fct, user_id)
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

    result_proxy = conn.execute(f"""
    SELECT sys.name AS system_name, company_id, sys.kafka_servers, sa.name, sa.source_system, sa.target_system, 
    sa.creator_id, sa.logic, sa.status, sa.datetime AS created_at, sa.description, sa.is_multi_source 
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN stream_apps sa on sys.name = sa.source_system
    WHERE agf.user_id='{user_id}' AND source_system='{system_name}';""")
    engine.dispose()
    streams = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the streams
    return jsonify({"stream_apps": streams})


@api_stream_app.route(f"{prefix}/stream_apps/<string:user_id>/<string:system_url>/<string:stream_name>")
@api_stream_app.route(f"{prefix}/stream_apps/<string:user_id>/<string:system_url>/<string:stream_name>/")
def stream_per_system(user_id, system_url, stream_name):
    """
    Returns a stream app in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found stream apps
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/stream_apps/<string:user_id>/<string:system_url>"
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

    result_proxy = conn.execute(f"""
    SELECT sys.name AS system_name, company_id, sys.kafka_servers, sa.name, sa.source_system, sa.target_system, 
    sa.creator_id, sa.logic, sa.status, sa.datetime AS created_at, sa.description, sa.is_multi_source 
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN stream_apps sa on sys.name = sa.source_system
    WHERE agf.user_id='{user_id}' AND source_system='{system_name}' AND sa.name='{stream_name}';""")
    engine.dispose()
    streams = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the single stream app
    return jsonify({"stream_apps": streams})


@api_stream_app.route(f"{prefix}/stream_apps/<string:user_id>/<string:system_url>", methods=['POST', 'PUT'])
def create_stream_app(user_id, system_url):
    """
    Create a stream app by sending a json like:
    "stream_app": {
        "name": "stream_app_1",
        "target_system": "cz.icecars.iot4cps-wp5-CarFleet.Car2",
        "logic": "SELECT * FROM cz.icecars.iot4cps-wp5-CarFleet.Car1;",
        "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
    }
    :return: return a json with the new stream_app and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/create_stream_app/<string:user_id>/<string:system_url>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"name", "target_system"}
    new_stream_app = request.json

    if not isinstance(new_stream_app, dict):
        msg = f"The new stream app can't be found in request json."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    if not req_keys.issubset(set(new_stream_app.keys())):
        msg = f"The stream app must contain the keys '{req_keys}', missing '{req_keys - set(new_stream_app.keys())}'."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    # 3) check if the user is allowed to get the system
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

    # 4) create the stream app or warn if it exists.
    # If the stream-app exists and the method is POST, return without change. If the method is PUT, overwrite
    stream_name = new_stream_app["name"]
    result_proxy = conn.execute(
        f"SELECT source_system, name FROM stream_apps "
        f"WHERE source_system='{system_name}' AND name='{stream_name}';")
    stream_apps = [dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the provided target_system really exists
    target_system = decode_sys_url(new_stream_app.get("target_system", ""))
    result_proxy = conn.execute(f"SELECT count(*) FROM systems WHERE name='{target_system}';")
    target_systems_res = [dict(c.items()) for c in result_proxy.fetchall()]
    if target_systems_res[0].get("count", 0) < 1:
        engine.dispose()
        print(target_systems_res)
        msg = f"The target system '{target_system}' does not exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    new_stream_apps = [{"name": stream_name,
                        "source_system": system_name,
                        "target_system": new_stream_app["target_system"],
                        "logic": new_stream_app.get("logic", ""),
                        "is_multi_source": new_stream_app.get("is_multi_source", False),
                        "creator_id": user_id,
                        "status": "init",
                        "datetime": get_datetime(),
                        "description": new_stream_app.get("description", "")}]
    if len(stream_apps) > 0:
        # If the stream-app exists and the method is POST, return without change. If the method is PUT, overwrite
        if request.method == "POST":
            engine.dispose()
            msg = f"The stream app with name '{stream_name}' for system '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208
        else:  # PUT overwrite
            query = db.update(app.config["tables"]["stream_apps"]).where(
                ("name" == stream_name and "source_system" == system_name))
            conn.execute(query, new_stream_apps)
    else:
        query = db.insert(app.config["tables"]["stream_apps"])
        conn.execute(query, new_stream_apps)

    engine.dispose()
    # return created stream app
    return jsonify({"stream_apps": new_stream_apps})


@api_stream_app.route(f"{prefix}/delete_stream_app/<string:user_id>/<string:system_url>/<string:stream_name>",
                      methods=['DELETE'])
def delete_stream_app(user_id, system_url, stream_name):
    """
    Delete a stream app
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_stream_app/<string:user_id>/<string:system_url>/<string:stream_name>"
    user_id = get_user_id(fct, user_id)
    system_name = decode_sys_url(system_url)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the user is admin of the system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(
        f"SELECT '1' FROM is_admin_of_sys "
        f"INNER JOIN stream_apps ON source_system=system_name "
        f"WHERE user_id='{str(user_id)}' AND system_name='{system_name}' AND name='{stream_name}';")
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from the system '{system_name}' or the stream doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) delete the instances from stream apps
    query = f"""DELETE FROM stream_apps
        WHERE source_system='{system_name}' AND name='{stream_name}';"""
    conn.execute(query)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted stream app '{stream_name}' from system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
