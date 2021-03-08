import urllib

import requests
import sqlalchemy as db

from passlib.hash import sha256_crypt

# Must be imported to use the app config
from flask import current_app as app
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, jsonify


# prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
# api_auth = Blueprint("api_auth", __name__)

def get_user_id(fct, user_id):
    # check if the value is an integer
    try:
        user_id = int(user_id)
    except ValueError as e:
        msg = "The user_id must be an integer."
        app.logger.error(f"{fct}: {msg}")
        return False, msg, 400
    return user_id


def authorize_request(user_id, fct, request):
    # check if the value is an integer
    user_id = get_user_id(fct, user_id)

    # check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    if user_id >= 0:  # Request from an identity-service person
        res = get_user_from_identity_service(user_id)
        result = res.json()
        if res.status_code not in [200, 201, 202] or str(user_id) != result.get("id", None):
            msg = f"Authentication error for user '{user_id}'."
            app.logger.error(f"{fct}: {msg}")
            return False, msg, 401
        else:
            # Return the result
            pass

    else:  # Request from a Panta Rhei user, check session_id
        app.logger.debug(f"{fct}: Fetch all systems for the requesting user '{user_id}'.")

        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()
        result_proxy = conn.execute(f"SELECT id, password FROM users WHERE id='{user_id}';")
        engine.dispose()
        users = [dict(c.items()) for c in result_proxy.fetchall()]

        if len(users) == 0:
            msg = f"Authentication error, user with id '{user_id}' not found."
            app.logger.error(f"{fct}: {msg}")
            return False, msg, 400

        if not sha256_crypt.verify(request.headers["Authorization"].strip(), hash=users[0]["password"]):
            msg = f"Authentication error, password is incorrect."
            app.logger.error(f"{fct}: {msg}")
            return False, msg, 401

    msg = f"Authorized request from user '{user_id}'."
    app.logger.info(f"{fct}: {msg}")
    return True, msg, 200


def get_user_from_identity_service(user_id):
    bearer_token = request.headers["Authorization"].strip()
    url = urllib.parse.urljoin(app.config.get("IASSET_SERVER"), "/identity/person/", str(user_id))
    res = requests.get(url=url,
                       headers={'content-type': 'application/json',
                                'Authorization': bearer_token})
    return res

def get_party_from_identity_service(partyIds):
    bearer_token = request.headers["Authorization"].strip()
    url = urllib.parse.urljoin(app.config.get("IASSET_SERVER"), "/identity/parties/", str(partyIds))
    res = requests.get(url=url,
                       headers={'content-type': 'application/json',
                                'Authorization': bearer_token})
    return res