import sqlalchemy as db
from flask import Blueprint, request, jsonify
# Must be imported to use the app config
from flask import current_app as app

from .api_auth import authorize_request, get_user_id
from ..utils.useful_functions import get_datetime, decode_sys_url, \
    strip_dict

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_aas = Blueprint("api_aas", __name__)


@api_aas.route(f"{prefix}/aas_connections")
@api_aas.route(f"{prefix}/aas_connections/")
@api_aas.route(f"{prefix}/aas_connections/<string:any>")
@api_aas.route(f"{prefix}/aas_connections/<string:any>/")
def aas_no_sys(any=None):
    return jsonify({"value": "Please specify an user id and a system name.",
                    "url": f"{prefix}/aas_connections/<string:user_id>/<string:system_name>", "status_code": 406}), 406


@api_aas.route(f"{prefix}/aas_connections/<string:user_id>/<string:system_url>", methods=['GET'])
# @api_client_app.route(f"{prefix}/aas_connections/<string:user_id>/<string:system_url>/", methods=['GET'])
def aas_per_system(user_id, system_url):
    """
    Searches for all aas connections in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found aas connections
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/aas_connections/<string:user_id>/<string:system_url>"
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all aas connections that belong to the user with id user_id and system_name
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
    SELECT clients.system_name, clients.name, creator.email AS contact_mail, clients.description, on_kafka, 
    clients.datetime AS datetime, submodel_element_collection
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN client_apps as clients on sys.name = clients.system_name
    INNER JOIN users as creator ON creator.id=clients.creator_id
    WHERE agf.user_id='{user_id}' AND clients.system_name='{system_name}';""")
    engine.dispose()
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the client apps
    return jsonify({"client_apps": clients})


@api_aas.route(f"{prefix}/client_apps/<string:user_id>/<string:system_url>/<string:client_name>")
# @api_client_app.route(f"{prefix}/client_apps/<string:user_id>/<string:system_url>/<string:client_name>/")
def client_per_system(user_id, system_url, client_name):
    """
    Returns a specific client app in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param client_name: name of the client app, unique within the system.
    :return: Json of all found client apps
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/client_apps/<string:user_id>/<string:system_url>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all client apps that belong to the user with id user_id and system_name
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
    SELECT sys.name AS system_name, company_id, sys.kafka_servers, ca.name, ca.system_name, ca.creator_id,  
    ca.submodel_element_collection, ca.on_kafka, ca.key, ca.datetime AS created_at, ca.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN client_apps AS ca on sys.name = ca.system_name
    WHERE agf.user_id='{user_id}' AND ca.system_name='{system_name}' AND ca.name='{client_name}';""")
    engine.dispose()
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the single client app
    return jsonify({"client_apps": clients})


@api_aas.route(f"{prefix}/client_apps/<string:user_id>/<string:system_url>", methods=['POST', 'PUT'])
def create_client_app(user_id, system_url):
    """
    Create a client app by sending a json like:
    "client_app": {
    "name": "client_app_1",
    "submodel_element_collection": "https://iasset.salzburgresearch.at/registry/sec_uuid",
    "on_kafka": True,
    "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
    }
    :return: return a json with the new stream_app and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/client_apps/<string:user_id>/<string:system_url>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"name"}
    new_client_app = request.json

    if not isinstance(new_client_app, dict):
        msg = f"The new client app can't be found in request json."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    if not req_keys.issubset(set(new_client_app.keys())):
        msg = f"The client app must contain the keys '{req_keys}', missing '{req_keys - set(new_client_app.keys())}'."
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

    # 4) create the client app or warn if it exists.
    # If the client app exists and the method is POST, return without change. If the method is PUT, overwrite
    client_name = new_client_app["name"]
    result_proxy = conn.execute(
        f"SELECT system_name, name FROM client_apps "
        f"WHERE system_name='{system_name}' AND name='{client_name}';")
    client_apps = [dict(c.items()) for c in result_proxy.fetchall()]

    new_client_apps = [{"name": client_name,
                        "system_name": system_name,
                        "submodel_element_collection": new_client_app.get("submodel_element_collection", ""),
                        "on_kafka": new_client_app.get("on_kafka", True),
                        "creator_id": user_id,
                        "key": "",
                        "datetime": get_datetime(),
                        "description": new_client_app.get("description", "")}]

    if len(client_apps) > 0:
        # If the stream-app exists and the method is POST, return without change. If the method is PUT, overwrite
        if request.method == "POST":
            engine.dispose()
            msg = f"The client app with name '{client_name}' for system '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208

        else:  # PUT
            query = db.update(app.config["tables"]["client_apps"]).where(
                ("name" == client_name and "system_name" == system_name))
            conn.execute(query, new_client_apps)

    else:  # doesn't exist yet
        query = db.insert(app.config["tables"]["client_apps"])
        conn.execute(query, new_client_apps)

    engine.dispose()
    # return created client app
    return jsonify({"client_apps": new_client_apps})


@api_aas.route(f"{prefix}/delete_client_app/<string:user_id>/<string:system_url>/<string:client_name>",
               methods=['DELETE'])
def delete_client_app(user_id, system_url, client_name):
    """
    Delete a client app
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_client_app/<string:user_id>/<string:system_url>/<string:client_name>"
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
        f"INNER JOIN client_apps ca on is_admin_of_sys.system_name = ca.system_name "
        f"WHERE user_id='{str(user_id)}' AND ca.system_name='{system_name}' AND name='{client_name}';")
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from the system '{system_name}' or the client doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) delete the instances from client apps
    query = f"""DELETE FROM client_apps
        WHERE system_name='{system_name}' AND name='{client_name}';"""
    conn.execute(query)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted client app '{client_name}' from system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
