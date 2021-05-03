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
def aass_per_system(user_id, system_url):
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
    SELECT aas.system_name, aas.name, aas.registry_uri, creator.email AS contact_mail, aas.datetime AS created_at, 
        aas.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN aas on sys.name = aas.system_name
    INNER JOIN users as creator ON creator.id=aas.creator_id
    WHERE agf.user_id='{user_id}' AND aas.system_name='{system_name}';""")
    engine.dispose()
    aas_cons = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the client apps
    return jsonify({"aas_connections": aas_cons})


@api_aas.route(f"{prefix}/aas_connections/<string:user_id>/<string:system_url>/<string:aas_name>")
def aas_per_system(user_id, system_url, aas_name):
    """
    Returns a specific aas connection in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param aas_name: name of the connected aas, unique within the system.
    :return: Json of all found client apps
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/aas_connections/<string:user_id>/<string:system_url>/<string:aas_name>"
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
    SELECT aas.system_name, aas.name, aas.registry_uri, creator.email AS contact_mail, aas.datetime AS created_at, 
        aas.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN aas on sys.name = aas.system_name
    INNER JOIN users as creator ON creator.id=aas.creator_id
    WHERE agf.user_id='{user_id}' AND aas.system_name='{system_name}' AND aas.name='{aas_name}';""")
    engine.dispose()
    aas_cons = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the single aas connection
    return jsonify({"aas_connections": aas_cons})


@api_aas.route(f"{prefix}/aas_connections/<string:user_id>/<string:system_url>", methods=['POST', 'PUT'])
def create_aas_con(user_id, system_url):
    """
    Create an aas connection by sending a json like:
    {
        "name": "aas_conn_1",
        "registry_uri": "https://iasset.salzburgresearch.at/registry/sec_uuid",
        "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
    }
    :return: return a json with the new aas connection and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/aas_connections/<string:user_id>/<string:system_url>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"name"}
    new_aas_conn = request.json

    if not isinstance(new_aas_conn, dict):
        msg = f"The new aas connection can't be found in request json."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    if not req_keys.issubset(set(new_aas_conn.keys())):
        msg = f"The aas connection must contain the keys '{req_keys}', missing '{req_keys - set(new_aas_conn.keys())}'."
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

    # 4) create the aas conn or warn if it exists.
    # If the aas conn exists and the method is POST, return without change. If the method is PUT, overwrite
    aas_conn_name = new_aas_conn["name"]
    result_proxy = conn.execute(
        f"SELECT system_name, name FROM aas "
        f"WHERE system_name='{system_name}' AND name='{aas_conn_name}';")
    aas_conn_apps = [dict(c.items()) for c in result_proxy.fetchall()]

    new_aas_conn = [{"name": aas_conn_name,
                     "system_name": system_name,
                     "registry_uri": new_aas_conn.get("registry_uri", ""),
                     "creator_id": user_id,
                     "datetime": get_datetime(),
                     "description": new_aas_conn.get("description", "")}]

    if len(aas_conn_apps) > 0:
        # If the aas-conn exists and the method is POST, return without change. If the method is PUT, overwrite
        if request.method == "POST":
            engine.dispose()
            msg = f"The aas connection with name '{aas_conn_name}' for system '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208

        else:  # PUT
            query = db.update(app.config["tables"]["aas"]).where(
                ("name" == aas_conn_name and "system_name" == system_name))
            conn.execute(query, new_aas_conn)

    else:  # doesn't exist yet
        query = db.insert(app.config["tables"]["aas"])
        conn.execute(query, new_aas_conn)

    engine.dispose()
    # return created client app
    return jsonify({"aas_connections": new_aas_conn})


@api_aas.route(f"{prefix}/delete_aas_connection/<string:user_id>/<string:system_url>/<string:aas_conn_name>",
               methods=['DELETE'])
def delete_aas_conn(user_id, system_url, aas_conn_name):
    """
    Delete an aas connection
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_aas_connection/<string:user_id>/<string:system_url>/<string:client_name>"
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
        f"INNER JOIN aas on is_admin_of_sys.system_name = aas.system_name "
        f"WHERE user_id='{str(user_id)}' AND aas.system_name='{system_name}' AND name='{aas_conn_name}';")
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from the system '{system_name}' or the aas connection doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) delete aas connection
    query = f"""DELETE FROM aas
        WHERE system_name='{system_name}' AND name='{aas_conn_name}';"""
    conn.execute(query)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted aas connection '{aas_conn_name}' from system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
