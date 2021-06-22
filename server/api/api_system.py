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
api_system = Blueprint("api_system", __name__)


@api_system.route(f"{prefix}", methods=['GET'])
@api_system.route(f"{prefix}/", methods=['GET'])
def test_api():
    return jsonify({"value": "You are connected with the awesome distribution network.",
                    "url": f"{prefix}", "status_code": 200}), 200


@api_system.route(f"{prefix}/api", methods=['GET'])
@api_system.route(f"{prefix}/api/", methods=['GET'])
def redirect_to_swagger():
    base_url = request.base_url.split(f"{prefix}/api")[0].replace(f"{prefix}/api", "")
    print(base_url)
    return redirect(f"{base_url}{prefix}/swagger-ui.html")


@api_system.route(f"{prefix}/systems_by_person", methods=['GET'])
@api_system.route(f"{prefix}/systems_by_person/", methods=['GET'])
def systems_by_person_no_id():
    return jsonify({"value": "Please specify a personId/user_id",
                    "url": f"{prefix}/systems_by_person/<int:user_id>", "status_code": 406}), 406


@api_system.route(f"{prefix}/systems_by_person/<string:user_id>", methods=['GET'])
def systems_by_person(user_id):
    """
    Searches for all systems in the distribution network of which the user is admin of. The user_id must be
    authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :return: Json of all found systems
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/systems_by_person/<string:user_id>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all systems that belong to the user with id user_id
    # cases without authorization are returned, here the user is definitely permitted to request the data
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(f"""
    SELECT sys.name AS system_name, com.name AS company, com.id AS company_id, sys.description, kafka_servers, 
    sys.datetime AS created_at, creator_id, creator.first_name, creator.sur_name, creator.email, sys.*,
    mqtt.server as mqtt_server, mqtt.version as mqtt_version, mqtt.topic as mqtt_topic
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as creator ON creator.id=agf.creator_id 
    FULL JOIN mqtt_broker AS mqtt ON sys.name=mqtt.system_name 
    WHERE agf.user_id='{user_id}';""")
    engine.dispose()
    systems = [dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Structure the raw data and return
    for i, res in enumerate(systems):
        sys = dict()
        res = {k: v for k, v in res.items() if v}
        for key in ["system_name", "created_at", "company", "description", "company_id", "kafka_servers",
                    "company_id"]:
            sys[key] = safe_strip(res.get(key, ""))
        sys["creator"] = {"creator_id": res.get("creator_id", ""),
                          "first_name": res.get("first_name", ""),
                          "sur_name": res.get("sur_name", ""),
                          "email": res.get("email", "")}
        sys["mqtt_broker"] = {"mqtt_server": res.get("mqtt_server", ""),
                              "mqtt_version": res.get("mqtt_version", ""),
                              "mqtt_topic": res.get("mqtt_topic", "")}
        systems[i] = sys

    return jsonify({"systems": systems})


@api_system.route(f"{prefix}/systems_by_person/<string:user_id>", methods=['POST', 'PUT'])
def create_systems_by_person(user_id):
    """
    Create a system by sending a json like:
    {
        "company_id": -11,
        "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit.",
        "kafka_server": "",
        "mqtt_broker": {
            "mqtt_server": "",
            "mqtt_version": ""
        },
        "workcenter": "iot4cps-wp5-CarFleet",
        "station": "Car3"
    }
    :return: return a json with the new system and admin_of_sys
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/create_system/<string:user_id>"
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the system to create has the correct structure
    req_keys = {"company_id", "station", "workcenter"}
    new_system = request.json

    if not isinstance(new_system, dict):
        msg = f"The new system can't be found in request json."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    if not req_keys.issubset(set(new_system.keys())):
        msg = f"The new system must contain the keys '{req_keys}', '{req_keys - set(new_system.keys())}' not found."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    company_id = new_system["company_id"]
    if company_id * int(user_id) < 0:
        msg = f"The company_id and user_id must be both either smaller or greater than zero."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    # 3) check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    if user_id >= 0:  # Request from an identity-service person
        # create user and company if they don't exist
        _, user_res, status_code = get_user_from_identity_service(fct=fct, user_id=user_id)
        authorized, party_res, status_code = get_party_from_identity_service(fct, user_id=user_id, party_id=company_id)
        if status_code != 200:
            msg = f"The company with id '{company_id}' is not registered in the identity service."
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

        # create users if not exists
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()
        result_proxy = conn.execute(f"SELECT id FROM users WHERE id='{user_id}';")
        users = [dict(c.items()) for c in result_proxy.fetchall()]
        if len(users) == 0:
            query = db.insert(app.config["tables"]["users"])
            values_list = [{"id": user_id,
                            "first_name": user_res.get("firstName", ""),
                            "sur_name": user_res.get("familyName", ""),
                            "email": user_res.get("contact", {}).get("electronicMail", ""),
                            "bearer_token": request.headers["Authorization"].strip()
                            }]
            conn.execute(query, values_list)

        # create company if not exists
        result_proxy = conn.execute(f"SELECT id, domain, enterprise FROM companies WHERE id='{company_id}';")
        companies = [dict(c.items()) for c in result_proxy.fetchall()]
        if len(companies) == 0:
            country = party_res["postalAddress"]["country"]["name"].get("value")
            domain = app.config["COUNTRY_CODES"].get(country, "com").lower()  # com is the default
            enterprise = str(company_id)

            query = db.insert(app.config["tables"]["companies"])
            values_list = [{"id": company_id,
                            "name": party_res["partyName"][0]["name"]["value"],
                            "domain": domain,
                            "enterprise": enterprise,
                            "description": party_res["industryClassificationCode"]["value"],
                            'datetime': get_datetime()
                            }]
            conn.execute(query, values_list)
        else:
            domain = companies[0]["domain"].strip()
            enterprise = companies[0]["enterprise"].strip()

        # create is_admin_of_com if not exists
        result_proxy = conn.execute(
            f"SELECT '1' FROM is_admin_of_com WHERE user_id='{user_id}' AND company_id='{company_id}';")
        admins = [dict(c.items()) for c in result_proxy.fetchall()]
        if len(admins) == 0:
            query = db.insert(app.config["tables"]["is_admin_of_com"])
            values_list = [{"user_id": user_id,
                            "company_id": company_id,
                            "creator_id": user_id,
                            'datetime': get_datetime()
                            }]
            conn.execute(query, values_list)

    else:  # the case they exist in the Digital Twin Platform
        # fetch company and check if the users it authorized to create a system
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()
        result_proxy = conn.execute(
            f"SELECT user_id AS creator_id, company_id, domain, enterprise "
            f"FROM is_admin_of_com "
            f"INNER JOIN companies AS com ON com.id=company_id "
            f"WHERE user_id='{user_id}' AND company_id='{company_id}';")
        engine.dispose()
        user_comp = [dict(c.items()) for c in result_proxy.fetchall()]
        if len(user_comp) == 0:
            msg = f"User '{user_id}' is not permitted to create a system for company '{company_id}'."
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 400}), 400
        domain = user_comp[0]["domain"].strip()
        enterprise = user_comp[0]["enterprise"].strip()

    # 4) create the system instances or warn if it exists.
    # load domain and enterprise and then build the system name :)
    workcenter = new_system["workcenter"].strip()
    station = new_system["station"].strip()
    if not (is_valid_level_name_string(workcenter) and is_valid_level_name_string(station)):
        msg = f"The provided workcenter and/or station are not valid level names."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    system_name = f"{domain}.{enterprise}.{workcenter}.{station}"

    # Insert new system
    # If the system exists and the method is POST, return without change. If the method is PUT, overwrite
    result_proxy = conn.execute(
        f"SELECT name FROM systems "
        f"WHERE name='{system_name}';")
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    new_systems = [{"name": system_name,
                    "company_id": company_id,
                    "workcenter": workcenter,
                    "station": station,
                    "kafka_servers": new_system.get("kafka_servers", "").strip(),
                    "datetime": get_datetime(),
                    "description": new_system.get("description", "")}]
    if len(systems) > 0:
        # If the system exists and the method is POST, return without change. If the method is PUT, overwrite
        if request.method == "POST":
            msg = f"The system with name '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208
    else:
        query = db.insert(app.config["tables"]["systems"])
        conn.execute(query, new_systems)

    # Insert admin of new system
    result_proxy = conn.execute(
        f"SELECT system_name, user_id FROM is_admin_of_sys "
        f"WHERE system_name='{system_name}' AND user_id='{user_id}';")
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    new_admin_of_sys = [
        {'user_id': user_id,
         'system_name': system_name,
         'creator_id': user_id,
         'datetime': get_datetime()}]
    if len(systems) > 0:
        msg = f"The admin_of_sys with name '{system_name}' and user '{user_id}' already exists."
        app.logger.warning(f"{fct}: {msg}")
        # return jsonify({"value": msg, "url": fct, "status_code": 208}), 208
    else:
        query = db.insert(app.config["tables"]["is_admin_of_sys"])
        conn.execute(query, new_admin_of_sys)

    # add mqtt cluster if provided
    if "mqtt_broker" in new_system.keys():
        app.logger.warning(f"{fct}: The MQTT messaging is not implemented yet.")
        mqtt_broker = new_system["mqtt_broker"]
        mqtt_server = mqtt_broker.get("mqtt_server", "")
        if not mqtt_server or mqtt_server == "":
            app.logger.warning(f"{fct}: The MQTT broker can't be specified as mqtt_server is not specified.")

        # Insert mqtt broker
        result_proxy = conn.execute(f"SELECT '1' FROM mqtt_broker WHERE system_name='{system_name}';")
        mqtt_brokers = [dict(c.items()) for c in result_proxy.fetchall()]
        new_mqtt_brokers = [
            {'system_name': system_name,
             'server': mqtt_server,
             'version': mqtt_broker.get("mqtt_version", ""),
             'topic': system_name.replace(".", "/")}]
        if len(mqtt_brokers) > 0:
            msg = f"The mqtt_broker for system '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
        else:
            query = db.insert(app.config["tables"]["mqtt_broker"])
            conn.execute(query, new_mqtt_brokers)

    engine.dispose()

    # 5) Create kafka system topics
    try:
        app.kafka_interface.create_system_topics(system_name=system_name)
    except Exception as e:
        app.logger.warning(f"{fct}: Couldn't create Kafka topics for system '{system_name}, {e}")

    # return system
    return jsonify({"systems": new_systems, "is_admin_of_sys": new_admin_of_sys})


@api_system.route(f"{prefix}/delete_system/<string:user_id>/<string:system_url>", methods=['DELETE'])
def delete_systems(system_url, user_id):
    """
    Delete a system
    :return: return nothing
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_system/<string:system_name>/<string:user_id>"
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
        f"WHERE user_id='{str(user_id)}' AND system_name='{system_name}';")
    engine.dispose()
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        msg = f"User '{user_id}' is not permitted to delete the system '{system_name}' or it doesn't exist."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) delete the instances from systems, is_admin_of_sys
    transaction = conn.begin()
    # Delete single mqtt_broker
    query = """DELETE FROM mqtt_broker
        WHERE system_name='{}';""".format(system_name)
    conn.execute(query)
    # Delete is_admin_of_sys instance(s)
    query = """DELETE FROM is_admin_of_sys
        WHERE system_name='{}';""".format(system_name)
    conn.execute(query)
    # Delete single system
    query = """DELETE FROM systems
        WHERE name='{}';""".format(system_name)
    conn.execute(query)
    engine.dispose()

    # 4) Delete Kafka topics
    if app.kafka_interface.delete_system_topics(system_name=system_name):
        transaction.commit()
        app.logger.info("The system '{}' was deleted.".format(system_name))
        flash("The system '{}' was deleted.".format(system_name), "success")
    else:
        transaction.rollback()
        app.logger.warning(f"{fct}: The system '{system_name}' could not be deleted, returned False")
        flash("The system '{}' couldn't be deleted.".format(system_name), "danger")

    # 5) return
    return jsonify({"url": fct, "status_code": 204}), 204

