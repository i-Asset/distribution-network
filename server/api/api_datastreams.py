import sqlalchemy as db
from flask import Blueprint, request, jsonify
# Must be imported to use the app config
from flask import current_app as app

from .api_auth import authorize_request, get_user_id
from ..utils.useful_functions import get_datetime, decode_sys_url, \
    strip_dict

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_datastreams = Blueprint("api_datastream", __name__)


@api_datastreams.route(f"{prefix}/datastreams")
@api_datastreams.route(f"{prefix}/datastreams/")
@api_datastreams.route(f"{prefix}/datastreams/<string:any>")
@api_datastreams.route(f"{prefix}/datastreams/<string:any>/")
def datastreams_no_sys(any=None):
    return jsonify({"value": "Please specify an user id and a system name.",
                    "url": f"{prefix}/datastreams/<string:user_id>/<string:system_name>", "status_code": 406}), 406


@api_datastreams.route(f"{prefix}/datastreams/<string:user_id>/<string:system_url>", methods=['GET'])
def datastreams_per_system(user_id, system_url):
    """
    Searches for all datastreams in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found datastreams
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/datastreams/<string:user_id>/<string:system_url>"
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Cases without authorization are returned, here the user is definitely permitted to request the data
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

    # 3) Fetch all datastreams that belong to the user with id user_id and system_name
    result_proxy = conn.execute(f"""
    SELECT ds.system_name, shortname, ds.name, thing_name, client_name, ds.resource_uri,
        creator.email AS contact_mail, ds.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN datastreams ds on sys.name = ds.system_name
    INNER JOIN users as creator ON creator.id=ds.creator_id
    WHERE agf.user_id='{user_id}' AND ds.system_name='{system_name}';""")
    engine.dispose()
    datastreams = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the datastreams
    return jsonify({"datastreams": datastreams})


@api_datastreams.route(f"{prefix}/datastreams_per_client/<string:user_id>/<string:system_url>/<string:client_name>")
def datastreams_per_client(user_id, system_url, client_name):
    """
    Returns the datastream that belong to a client app in the distribution network of which the user is admin of.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param client_name: name of the client app, unique within the system.
    :return: Json of all datastreams of the client app
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/datastreams_per_client/<string:user_id>/<string:system_url>/<string:client_name>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all datastreams that belong to the user with id user_id and system_name
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
    SELECT ds.system_name, shortname, ds.name, thing_name, client_name, ds.resource_uri,
        creator.email AS contact_mail, ds.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN datastreams ds on sys.name = ds.system_name
    INNER JOIN users as creator ON creator.id=ds.creator_id
    WHERE agf.user_id='{user_id}' AND ds.system_name='{system_name}' AND ds.client_name='{client_name}';""")
    engine.dispose()
    datastreams = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the datastreams of the client
    return jsonify({"datastreams": datastreams})


@api_datastreams.route(f"{prefix}/datastreams_per_thing/<string:user_id>/<string:system_url>/<string:thing_name>")
def datastreams_per_thing(user_id, system_url, thing_name):
    """
    Returns the datastream that belong to an thing connection in the distribution network of which the user is admin of.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param thing_name: name of the thing connection, unique within the system.
    :return: Json of all datastreams of the client app
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/datastreams_per_thing/<string:user_id>/<string:system_url>/<string:thing_name>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all datastreams that belong to the user with id user_id and system_name
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
    SELECT ds.system_name, shortname, ds.name, thing_name, client_name, ds.resource_uri,
        creator.email AS contact_mail, ds.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN datastreams ds on sys.name = ds.system_name
    INNER JOIN users as creator ON creator.id=ds.creator_id
    WHERE agf.user_id='{user_id}' AND ds.system_name='{system_name}' AND thing_name='{thing_name}';""")
    engine.dispose()
    datastreams = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the datastreams of the thing connection
    return jsonify({"datastreams": datastreams})


@api_datastreams.route(f"{prefix}/datastreams/<string:user_id>/<string:system_url>", methods=['POST', 'PUT'])
def create_datastreams(user_id, system_url):
    """
    Create datastreams by sending a json like:
    [
        {
            "name": "Air Temperature",
            "shortname": "temperature",
            "description": "Air temperature measured in the connected car 1",
            "thing_name": "car",
            "client_name": "car_1"
        }
    ]
    :return: return an json with the new datastreams and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/datastreams/<string:user_id>/<string:system_url>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"name", "shortname", "thing_name", "client_name"}
    new_datastreams = request.json

    if not isinstance(new_datastreams, list):
        msg = f"The datastreams must be in an array."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    for new_ds in new_datastreams:
        if not isinstance(new_ds, dict):
            msg = f"The new datastreams can't be found in request json: '{new_ds}'."
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
        if not req_keys.issubset(set(new_ds.keys())):
            msg = f"The datastream must contain the keys '{req_keys}', missing '{req_keys - set(new_ds.keys())}': '{new_ds}'."
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

    # 5) Load the existing datastreams of the system
    all_client_apps = "'" + "','".join(tuple({ds["client_name"] for ds in new_datastreams})) + "'"
    all_thing_conns = "'" + "','".join(tuple({ds["thing_name"] for ds in new_datastreams})) + "'"

    result_proxy = conn.execute(
        f"SELECT DISTINCT ca.system_name, thing_name, ca.name AS client_name, ds.name, ds.shortname "
        f"FROM datastreams AS ds "
        f"INNER JOIN client_apps AS ca ON ca.name=ds.client_name "
        f"WHERE ca.system_name='{system_name}' AND ds.system_name='{system_name}'"
        f"AND ca.name IN ({all_client_apps}) AND thing_name IN ({all_thing_conns});")
    existing_datastreams = [dict(c.items()) for c in result_proxy.fetchall()]

    new_ds = list()
    already_existing = list()
    for ds in new_datastreams:
        for ex_ds in existing_datastreams:
            if ds["shortname"] == ex_ds["shortname"] and ds["client_name"] == ex_ds["client_name"] and \
                    ds["thing_name"] == ex_ds["thing_name"]:
                already_existing.append(ds["shortname"])
        new_ds.append({
            "shortname": ds["shortname"],
            "name": ds["name"],
            "system_name": system_name,
            "thing_name": ds["thing_name"],
            "client_name": ds["client_name"],
            "client_system_name": system_name,
            "description": ds.get("description", ""),
            "creator_id": user_id,
            "datetime": get_datetime()
        })
    # return jsonify({"thing_connections": existing_datastreams})

    # 4) create the datastreams or warn if at least one of the datastreams already exist.
    if len(already_existing) > 0:
        # If one of the exists and the method is POST, return without change. If the method is PUT, overwrite
        if request.method == "POST":
            engine.dispose()
            msg = f"The datastreams '{already_existing}' for system '{system_name}' already exist, abort request."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208

        else:  # PUT
            for ds in new_ds:
                query = db.update(app.config["tables"]["datastreams"]).where(
                    ("shortname" == ds["shortname"] and "thing_name" == ds["thing_name"] and
                     "system_name" == ds["system_name"]))
                conn.execute(query, ds)

    else:  # doesn't exist yet
        query = db.insert(app.config["tables"]["datastreams"])
        conn.execute(query, new_ds)

    engine.dispose()
    # return created datastreams
    return jsonify({"datastreams": new_ds})


@api_datastreams.route(f"{prefix}/delete_datastreams/<string:user_id>/<string:system_url>/<string:thing_name>",
                       methods=['DELETE'])
def delete_datastreams(user_id, system_url, thing_name):
    """
    Delete datastreams that are posted in the requests
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_datastreams/<string:user_id>/<string:system_url>/<string:thing_name>"
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
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from the system '{system_name}' or it doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) check if the datastreams to delete has the correct structure
    datastreams_to_delete = request.json

    if not isinstance(datastreams_to_delete, list):
        msg = f"The datastreams must be in an array."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    for ds_to_del in datastreams_to_delete:
        if not isinstance(ds_to_del, str):
            msg = f"The datastreams must be an array of strings: '{ds_to_del}'."
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    # 4) delete thing connection
    for ds_to_del in datastreams_to_delete:
        delete_stmt = db.delete(app.config["tables"]["datastreams"]).where(
                        (app.config["tables"]["datastreams"].c.shortname == ds_to_del and
                        app.config["tables"]["datastreams"].c.thing_name == thing_name and
                         app.config["tables"]["datastreams"].c.system_name == system_name)
                    )
        conn.execute(delete_stmt)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted datastreams '{datastreams_to_delete}' from '{thing_name}'" +
                    " in system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
