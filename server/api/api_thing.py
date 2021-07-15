import sqlalchemy as db
from flask import Blueprint, request, jsonify
# Must be imported to use the app config
from flask import current_app as app

from .api_auth import authorize_request, get_user_id
from ..utils.useful_functions import get_datetime, decode_sys_url, \
    strip_dict

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_thing = Blueprint("api_thing", __name__)


@api_thing.route(f"{prefix}/things")
@api_thing.route(f"{prefix}/things/")
@api_thing.route(f"{prefix}/things/<string:any>")
@api_thing.route(f"{prefix}/things/<string:any>/")
def thing_no_sys(any=None):
    return jsonify({"value": "Please specify an user id and a system name.",
                    "url": f"{prefix}/thing_connections/<string:user_id>/<string:system_name>", "status_code": 406}), 406


@api_thing.route(f"{prefix}/things/<string:user_id>/<string:system_url>", methods=['GET'])
def things_per_system(user_id, system_url):
    """
    Searches for all things in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :return: Json of all found things
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/thing_connections/<string:user_id>/<string:system_url>"
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all things that belong to the user with id user_id and system_name
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
    SELECT things.system_name, things.name, things.resource_uri, creator.email AS contact_mail, things.datetime AS created_at, 
        things.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN things on sys.name = things.system_name
    INNER JOIN users as creator ON creator.id=things.creator_id
    WHERE agf.user_id='{user_id}' AND things.system_name='{system_name}';""")
    engine.dispose()
    thing_cons = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the client apps
    return jsonify({"thing": thing_cons})


@api_thing.route(f"{prefix}/things/<string:user_id>/<string:system_url>/<string:thing_name>")
def thing_per_system(user_id, system_url, thing_name):
    """
    Returns a specific thing in the distribution network of which the user is admin of and belong to the system.
    The user_id must be authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :param system_url: system identifier whose levels are separated by '_' or '.'
    :param thing_name: name of the thing, unique within the system.
    :return: Json of all found thing apps
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/thing_connections/<string:user_id>/<string:system_url>/<string:thing_name>"
    authorized, msg, status_code = authorize_request(fct=fct, user_id=user_id)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all thing connections that belong to the user with id user_id and system_name
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
    SELECT things.system_name, things.name, things.resource_uri, creator.email AS contact_mail, things.datetime AS created_at, 
        things.description
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN things on sys.name = things.system_name
    INNER JOIN users as creator ON creator.id=things.creator_id
    WHERE agf.user_id='{user_id}' AND things.system_name='{system_name}' AND things.name='{thing_name}';""")
    engine.dispose()
    thing_cons = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Return the single thing
    return jsonify({"thing": thing_cons})


@api_thing.route(f"{prefix}/things/<string:user_id>/<string:system_url>", methods=['POST', 'PUT'])
def create_thing_con(user_id, system_url):
    """
    Create a thing connection by sending a json like:
    {
        "name": "thing_1",
        "resource_uri": "https://iasset.salzburgresearch.at/resource/sec_uuid",
        "description": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
    }
    :return: return a json with the new thing and metadata
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/thing_connections/<string:user_id>/<string:system_url>"
    system_name = decode_sys_url(system_url)
    user_id = get_user_id(fct, user_id)
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) check if the client to create has the correct structure
    req_keys = {"name"}
    new_thing = request.json

    if not isinstance(new_thing, dict):
        msg = f"The new thing can't be found in request json."
        app.logger.error(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 406}), 406
    if not req_keys.issubset(set(new_thing.keys())):
        msg = f"The thing connection must contain the keys '{req_keys}', missing '{req_keys - set(new_thing.keys())}'."
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

    # 4) create the thing conn or warn if it exists.
    # If the thing exists and the method is POST, return without change. If the method is PUT, overwrite
    thing_name = new_thing["name"]
    result_proxy = conn.execute(
        f"SELECT system_name, name FROM things "
        f"WHERE system_name='{system_name}' AND name='{thing_name}';")
    thing_apps = [dict(c.items()) for c in result_proxy.fetchall()]

    new_thing = {"name": thing_name,
                     "system_name": system_name,
                     "resource_uri": new_thing.get("resource_uri", ""),
                     "creator_id": user_id,
                     "datetime": get_datetime(),
                     "description": new_thing.get("description", "")}

    if request.method == "POST":
        if len(thing_apps) > 0:
            # If one of the exists and the method is POST, return without change. If the method is PUT, overwrite
            engine.dispose()
            msg = f"The thing connection with name '{thing_name}' for system '{system_name}' already exists."
            app.logger.warning(f"{fct}: {msg}")
            return jsonify({"value": msg, "url": fct, "status_code": 208}), 208
        else:  # doesn't exist yet
            query = db.insert(app.config["tables"]["things"])
            conn.execute(query, new_thing)

    # If one of the exists and the method is POST, return without change. If the method is PUT, overwrite
    if request.method == "PUT":
        conn.execute(f"""
            INSERT INTO things 
                (name, system_name, resource_uri, description, creator_id, datetime) 
            VALUES ('{new_thing["name"]}', '{new_thing["system_name"]}', '{new_thing["resource_uri"]}', 
                '{new_thing["description"]}', '{new_thing["creator_id"]}', '{new_thing["datetime"]}') 
            ON CONFLICT (name, system_name) 
            DO UPDATE SET name='{new_thing["name"]}', system_name='{new_thing["system_name"]}', 
                resource_uri='{new_thing["resource_uri"]}', description='{new_thing["description"]}', 
                creator_id='{new_thing["creator_id"]}', datetime='{new_thing["datetime"]}';
        """)
        # This routine doesn't create anything if one of the instances already exists.
        # This behaviour is not desired for the PUT method.
        # query = db.update(app.config["tables"]["things"]).where(
        #     ("name" == thing_name and "system_name" == system_name))
        # conn.execute(query, new_thing)

    engine.dispose()
    # return created thing connection
    return jsonify({"things": [new_thing]})


@api_thing.route(f"{prefix}/delete_thing/<string:user_id>/<string:system_url>/<string:thing_name>",
                 methods=['DELETE'])
def delete_thing_conn(user_id, system_url, thing_name):
    """
    Delete a thing connection
    :return: return status json
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/delete_thing/<string:user_id>/<string:system_url>/<string:thing_name>"
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
        f"INNER JOIN things on is_admin_of_sys.system_name = things.system_name "
        f"WHERE user_id='{str(user_id)}' AND things.system_name='{system_name}' AND name='{thing_name}';")
    sys_admins = [dict(c.items()) for c in result_proxy.fetchall()]
    if len(sys_admins) == 0:
        engine.dispose()
        msg = f"User '{user_id}' isn't allowed to delete from the system '{system_name}' or the thing connection doesn't exist."
        app.logger.warning(f"{fct}: {msg}")
        return jsonify({"value": msg, "url": fct, "status_code": 400}), 400

    # 3) delete thing connection
    query = f"""DELETE FROM things
        WHERE system_name='{system_name}' AND name='{thing_name}';"""
    conn.execute(query)
    engine.dispose()

    # 5) return
    app.logger.info(f"{fct}: User '{user_id}' deleted thing connection '{thing_name}' from system '{system_name}'.")
    return jsonify({"url": fct, "status_code": 204}), 204
