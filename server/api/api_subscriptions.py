import sqlalchemy as db
from flask import Blueprint, request, jsonify
# Must be imported to use the app config
from flask import current_app as app

from .api_auth import authorize_request, get_user_id
from ..utils.useful_functions import get_datetime, decode_sys_url, encode_sys_url, strip_dict

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_subscriptions = Blueprint("api_subscriptions", __name__)


@api_subscriptions.route(f"{prefix}/subscriptions")
@api_subscriptions.route(f"{prefix}/subscriptions/")
@api_subscriptions.route(f"{prefix}/subscriptions/<string:any>")
@api_subscriptions.route(f"{prefix}/subscriptions/<string:any>/")
def datastreams_no_sys(any=None):
    return jsonify({"value": "Please specify an user id and a system name.",
                    "url": f"{prefix}/subscriptions/<string:user_id>/<string:system_name>", "status_code": 406}), 406


@api_subscriptions.route(f"{prefix}/subscriptions/<string:user_id>/<string:system_url>", methods=['GET'])
def subscriptions_per_system(user_id, system_url):
    """
    Searches for all subscriptions in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found datastreams
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/subscriptions/<string:user_id>/<string:system_url>"
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
    SELECT sc.shortname, ds.name, sc.thing_name, sc.thing_system_name, sc.client_name, sc.system_name, ds.resource_uri,
        creator.email AS contact_mail, ds.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
    INNER JOIN subscriptions sc on agf.system_name  = sc.system_name
    INNER JOIN datastreams ds on ds.shortname = sc.shortname AND ds.thing_name = sc.thing_name AND ds.system_name = sc.thing_system_name
    INNER JOIN users as creator ON creator.id=sc.creator_id
    WHERE agf.user_id='{user_id}' AND sc.system_name='{system_name}';""")
    engine.dispose()
    subscriptions = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    print(subscriptions)

    # 3) Return the datastreams
    return jsonify({"subscriptions": subscriptions})


@api_subscriptions.route(f"{prefix}/subscriptions_per_client/<string:user_id>/<string:system_url>/<string:client_name>")
def subscriptions_per_client(user_id, system_url, client_name):
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
    fct = f"{prefix}/subscriptions_per_client/<string:user_id>/<string:system_url>/<string:client_name>"
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
    SELECT sc.system_name, sc.shortname, ds.name, sc.thing_name, sc.client_name, ds.resource_uri,
        creator.email AS contact_mail, ds.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN subscriptions sc on sys.name = sc.system_name
    INNER JOIN datastreams ds on ds.shortname = sc.shortname AND ds.thing_name = sc.thing_name
    INNER JOIN users as creator ON creator.id=sc.creator_id
    WHERE agf.user_id='{user_id}' AND ds.system_name='{system_name}' AND sc.client_name='{client_name}';""")
    engine.dispose()
    subscriptions = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the datastreams of the client
    return jsonify({"subscriptions": subscriptions})


@api_subscriptions.route(f"{prefix}/subscriptions_per_client/<string:user_id>/<string:system_url>/<string:client_name>",
                         methods=['POST', 'PUT'])
def create_subscriptions(user_id, system_url, client_name):
    """
    Create datastreams by sending a json like:
    [
        {
          "shortname": "temperature",
          "thing_name": "Weatherstation_2",
          "system_name": "at.srfg.WeatherService.Stations"
        }
    ]
    :return: return an json with the new datastreams and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/subscriptions_per_client/<string:user_id>/<string:system_url>/<string:client_name>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"shortname", "thing_name", "system_name"}
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

    # 5) Load the existing subscriptions of the system
    all_thing_conns = "'" + "','".join(tuple({ds["thing_name"] for ds in new_datastreams})) + "'"

    result_proxy = conn.execute(
        f"SELECT DISTINCT system_name, thing_system_name, thing_name, client_name, shortname "
        f"FROM subscriptions AS sc "
        f"WHERE client_name = '{client_name}' AND system_name='{system_name}' "
        f"AND thing_name IN ({all_thing_conns});")
    existing_subscriptions = [dict(c.items()) for c in result_proxy.fetchall()]

    new_ds = list()
    already_existing = list()
    for ds in new_datastreams:
        for ex_ds in existing_subscriptions:
            if ds["shortname"] == ex_ds["shortname"] and \
                    client_name == ex_ds["client_name"] and system_name == ex_ds["system_name"] and \
                    ds["thing_name"] == ex_ds["thing_name"] and encode_sys_url(ds["system_name"]) == ex_ds["thing_system_name"]:
                already_existing.append(
                    {"shortname": ds["shortname"],
                     "thing_name": ds["thing_name"],
                     "system_name": encode_sys_url(ds["system_name"])}
                )
                break
        new_ds.append({
            "shortname": ds["shortname"],
            "thing_name": ds["thing_name"],
            "thing_system_name": encode_sys_url(ds["system_name"]),  # system of the thing
            "system_name": system_name,
            "client_name": client_name,
            "creator_id": user_id,
            "datetime": get_datetime()
        })
    # return jsonify({"thing_connections": existing_datastreams})

    # 4) create the datastreams or warn if at least one of the datastreams already exist.
    if request.method == "POST":
        if len(already_existing) > 0:
        # If one of the exists and the method is POST, return without change. If the method is PUT, overwrite
            engine.dispose()
            msg = (f"The datastream subscriptions '{already_existing}' for client '{client_name}' in "
                   + f"system '{system_name}' already exist, abort request.")
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208
        else:  # doesn't exist yet
            query = db.insert(app.config["tables"]["subscriptions"])
            conn.execute(query, new_ds)

    if request.method == "PUT":
        for ds in new_ds:
            conn.execute(f"""
                INSERT INTO subscriptions 
                    (shortname, thing_name, thing_system_name, client_name, system_name, creator_id, datetime) 
                VALUES ('{ds["shortname"]}', '{ds["thing_name"]}', '{ds["thing_system_name"]}', 
                    '{ds["client_name"]}', '{ds["system_name"]}', '{ds["creator_id"]}', '{ds["datetime"]}') 
                ON CONFLICT (shortname, thing_name, thing_system_name, client_name, system_name) 
                DO UPDATE SET shortname='{ds["shortname"]}', 
                    thing_name='{ds["thing_name"]}', thing_system_name='{ds["thing_system_name"]}',  
                    client_name='{ds["client_name"]}', system_name='{ds["system_name"]}', 
                    creator_id='{ds["creator_id"]}', datetime='{ds["datetime"]}';
            """)
            # This routine doesn't create anything if one of the instances already exists.
            # This behaviour is not desired for the PUT method.
            # (shortname='{ds["shortname"]}',
            # thing_name='{ds["thing_name"]}', thing_system_name='{ds["thing_system_name"]}',
            # client_name='{ds["client_name"]}', system_name='{ds["system_name"]}',
            # creator_id='{ds["creator_id"]}', datetime='{ds["datetime"]}'
            # query = db.update(app.config["tables"]["subscriptions"]).where((
            #     # "shortname" == ds["shortname"] and
            #      "thing_name" == ds["thing_name"] and "thing_system_name" == ds["thing_system_name"]
            #      # "client_name" == ds["client_name"] and "system_name" == ds["system_name"]
            #      ))
            # print(query)
            # conn.execute(query, ds)

    engine.dispose()
    # return created datastreams
    return jsonify({"subscriptions": new_ds})


@api_subscriptions.route(f"{prefix}/delete_subscriptions/<string:user_id>/<string:system_url>/<string:client_name>",
                         methods=['DELETE'])
def delete_subscriptions(user_id, system_url, client_name):
    """
    Delete datastream subscriptions that are posted in the requests
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_subscriptions/<string:user_id>/<string:system_url>/<string:client_name>"
    user_id = get_user_id(fct, user_id)
    system_name = decode_sys_url(system_url)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the user is admin of the system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(
        f"SELECT '1' FROM is_admin_of_sys iaos "
        f"INNER JOIN subscriptions sc ON sc.system_name = iaos.system_name "
        f"WHERE iaos.user_id='{str(user_id)}' AND sc.system_name='{system_name}' AND sc.client_name='{client_name}';")
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from client '{client_name}' in system '{system_name}' or it doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) check if the datastreams to delete has the correct structure
    req_keys = {"shortname", "thing_name", "system_name"}
    subscriptions_to_delete = request.json

    if not isinstance(subscriptions_to_delete, list):
        msg = f"The datastream subscriptions must be a list of objects."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    for ds_to_del in subscriptions_to_delete:
        if not isinstance(ds_to_del, dict):
            msg = f"The datastreams must be a list of objects: '{ds_to_del}'."
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
        if not req_keys.issubset(set(ds_to_del.keys())):
            msg = (f"The datastream subscriptions to delete must contain the keys '{req_keys}', "
                   + f"missing '{req_keys - set(ds_to_del.keys())}': '{ds_to_del}'.")
            app.logger.error(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 406}), 406

    # 4) delete subscriptions
    for ds_to_del in subscriptions_to_delete:
        conn.execute(f"""
        DELETE FROM subscriptions 
        WHERE shortname='{ds_to_del["shortname"]}' 
        AND thing_name='{ds_to_del["thing_name"]}' AND thing_system_name='{ds_to_del["system_name"]}' 
        AND client_name='{client_name}' AND system_name='{system_name}';
        """)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted datastream subscriptions '{subscriptions_to_delete}' " +
                    f"from '{client_name}' in system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
