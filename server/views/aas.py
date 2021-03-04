import os
import json
import time

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file
# Must be imported to use the app config
from flask import current_app as app, jsonify
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_level_name, valid_name, valid_url, strip_dict, \
    decode_sys_url, encode_sys_url

aas = Blueprint("aas", __name__)  # url_prefix="/aas")


@aas.route("/aas")
@is_logged_in
def show_all_aas():
    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients, for which systems the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT aas.system_name, aas.name, aas.registry_uri, creator.email AS contact_mail
    FROM aas
    INNER JOIN is_admin_of_sys AS agf ON aas.system_name=agf.system_name 
    INNER JOIN users as creator ON creator.id=agf.creator_id
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}'
    ORDER BY system_name, aas.name;""".format(user_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    aas_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    return render_template("/aas/aas.html", aas_list=aas_list)


@aas.route("/show_aas/<string:system_url>/<string:aas_name>")
@is_logged_in
def show_aas(system_url, aas_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch all clients for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT aas.system_name, com.name AS company_name, com.id AS company_id, aas.name, aas.registry_uri,
    creator.email AS contact_mail, aas.description, agent.id AS agent_id, aas.datetime AS datetime
    FROM aas
    INNER JOIN users as creator ON creator.id=aas.creator_id
    INNER JOIN systems AS sys ON aas.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE sys.name='{}' AND aas.name='{}';""".format(system_name, aas_name)
    result_proxy = conn.execute(query)
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched agents: {}".format(agents))

    # Check if the system exists and has agents
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this client doesn't exist.", "danger")
        return redirect(url_for("client_app.show_all_clients"))

    # Check if the current user is agent of the client's system
    if user_id not in [c["agent_id"] for c in clients]:
        engine.dispose()
        flash("You are not permitted see details this client.", "danger")
        return redirect(url_for("client_app.show_all_clients"))

    # if not, agents has at least one item
    payload = clients[0]
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    config = {"aas_name": aas_name,
              "system_name": system_name,
              "registry_uri": payload.get("aas_uri", "")}

    return render_template("/aas/show_aas.html", payload=payload, config=config)


# Client Form Class
class AasForm(Form):
    name = StringField("Name of the aas connection", [validators.Length(min=2, max=20), valid_name])
    registry_uri = StringField("AAS URI", [valid_url])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])


# Add client in clients view, redirect to systems
@aas.route("/add_aas")
@is_logged_in
def add_aas():
    # redirect to systems
    flash("Specify the system to which an aas connection should be added.", "info")
    return redirect(url_for("system.show_all_systems"))


# Add client in system view
@aas.route("/add_aas/<string:system_url>", methods=["GET", "POST"])
@is_logged_in
def add_client_for_system(system_url):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # The basic client form is used
    form = AasForm(request.form)
    form_name = form.name.data.strip()

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT system_name, agf.user_id AS agent_id
    FROM is_admin_of_sys AS agf
    WHERE agf.user_id='{}' AND system_name='{}';""".format(user_id, system_name)
    result_proxy = conn.execute(query)
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    # Check if the system exists and you are an admin
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist or you are not permitted to add clients to it.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # if not, clients has at least one item
    payload = clients[0]

    # Create a new client using the form"s input
    if request.method == "POST" and form.validate():
        # Create client and check if the combination of the system_uuid and name exists
        query = """SELECT system_name, name 
        FROM aas
        WHERE system_name='{}' AND name='{}';""".format(system_name, form_name)
        result_proxy = conn.execute(query)

        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["aas"])
            values_list = [{'name': form_name,
                            'system_name': system_name,
                            'registry_uri': form.registry_uri.data.strip(),
                            'creator_id': user_id,
                            "description": form.description.data,
                            'datetime': get_datetime()}]

            conn.execute(query, values_list)
            engine.dispose()

            msg = "An aas connection with name '{}' was registered for the system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("aas.show_aas",
                                system_url=encode_sys_url(system_name), aas_name=form_name))
        else:
            engine.dispose()
            msg = "The aas connection with name '{}' was already created for system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("aas.add_aas", system_url=encode_sys_url(system_name)))

    return render_template("/aas/add_aas.html", form=form, payload=payload)


# Delete client
@aas.route("/delete_aas/<string:system_url>/<string:aas_name>", methods=["GET"])
@is_logged_in
def delete_aas(system_url, aas_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT aas.system_name, aas.name, agf.user_id AS agent_id
    FROM aas
    INNER JOIN is_admin_of_sys AS agf ON aas.system_name=agf.system_name
    WHERE agf.user_id='{}' AND aas.system_name='{}';""".format(user_id, system_name)
    result_proxy = conn.execute(query)
    aas_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an agent
    if len(aas_list) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("aas.show_all_aas"))

    # Check if the current user is agent of the system
    if user_id not in [c["agent_id"] for c in aas_list]:
        engine.dispose()
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("aas.show_aas",
                                system_url=encode_sys_url(system_name), aas_list=aas_list))

    # Delete the specified client
    query = """DELETE FROM aas WHERE system_name='{}' AND name='{}';""".format(system_name, aas_name)
    conn.execute(query)
    engine.dispose()

    msg = f"The aas connection '{aas_name}' of the system '{system_name}' was deleted."
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
