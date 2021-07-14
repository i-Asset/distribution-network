import os

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file
# Must be imported to use the app config
from flask import current_app as app
from wtforms import Form, StringField, validators, TextAreaField

from server.utils.useful_functions import get_datetime, is_logged_in, valid_name, valid_url, strip_dict, \
    decode_sys_url, encode_sys_url

client_app = Blueprint("client_app", __name__)  # url_prefix="/comp")


@client_app.route("/clients")
@is_logged_in
def show_all_clients():
    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients, for which systems the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT clients.system_name, clients.name, creator.email AS contact_mail
    FROM client_apps AS clients
    INNER JOIN is_admin_of_sys AS agf ON clients.system_name=agf.system_name 
    INNER JOIN users as creator ON creator.id=agf.creator_id
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}'
    ORDER BY system_name, name;""".format(user_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    return render_template("/client_apps/clients.html", clients=clients)


@client_app.route("/show_client/<string:system_url>/<string:client_name>")
@is_logged_in
def show_client(system_url, client_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch all clients for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT clients.system_name, com.name AS company_name, com.id AS company_id, clients.name, 
    creator.email AS contact_mail, clients.description, agent.id AS agent_id, on_kafka, 
    clients.datetime AS datetime, clients.resource_uri
    FROM client_apps AS clients
    INNER JOIN users as creator ON creator.id=clients.creator_id
    INNER JOIN systems AS sys ON clients.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE sys.name='{}' AND clients.name='{}';""".format(system_name, client_name)
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

    if session.get("key_status") == "download":
        session["key_status"] = "init"
        # Delete the zip file for security reasons
        # make directory with unique name
        zipname = "ssl_{}_{}.zip".format(system_name, client_name)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dir_path, "keys", zipname)
        os.remove(path)
        app.logger.info("Removed key.")

    # if not, agents has at least one item
    payload = clients[0]
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    bootstrp_srv = app.config.get("KAFKA_BOOTSTRAP_SERVER")
    config = {"client_name": client_name,
              "system_name": system_name,
              "resource_uri": payload.get("resource_uri", ""),
              "kafka_bootstrap_servers": [bootstrp_srv if bootstrp_srv is not None else "localhost:9092"][0]}

    return render_template("/client_apps/show_client.html", payload=payload, config=config)


# Client Form Class
class ClientForm(Form):
    name = StringField("Name of the client application", [validators.Length(min=2, max=64), valid_name])
    # submodel_element_collection = StringField("Submodel element collection")
    resource_uri = StringField("Resource URI", [valid_url])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])


def create_keyfile(name="testclient", system_name="12345678"):
    import shutil
    # TODO create a real keyfile

    # make directory with unique name
    dirname = "ssl_{}_{}".format(encode_sys_url(system_name), name)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(dir_path, "keys", dirname)
    # print("Create dir with name: {}".format(path))
    os.mkdir(path)

    # Create keyfiles in the path
    with open(os.path.join(path, "cert-signed"), "w") as f:
        f.write("")
    with open(os.path.join(path, "client-cert-signed"), "w") as f:
        f.write("")

    # create zip archive and delete directory
    shutil.make_archive(path, "zip", path)
    app.logger.info("Create zip with name: {}".format(path))
    os.remove(os.path.join(path, "cert-signed"))
    os.remove(os.path.join(path, "client-cert-signed"))
    os.rmdir(path)


# Add client in clients view, redirect to systems
@client_app.route("/add_client")
@is_logged_in
def add_client():
    # redirect to systems
    flash("Specify the system to which a client should be added.", "info")
    return redirect(url_for("system.show_all_systems"))


# Add client in system view
@client_app.route("/add_client/<string:system_url>", methods=["GET", "POST"])
@is_logged_in
def add_client_for_system(system_url):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # The basic client form is used
    form = ClientForm(request.form)
    form_name = form.name.data.strip()

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT system_name, agf.user_id AS agent_id
    FROM systems AS sys
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
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
        FROM client_apps
        WHERE system_name='{}' AND name='{}';""".format(system_name, form_name)
        result_proxy = conn.execute(query)

        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["client_apps"])
            values_list = [{'name': form_name,
                            'system_name': system_name,
                            # 'submodel_element_collection': form.submodel_element_collection.data,
                            'resource_uri': form.resource_uri.data.strip(),
                            'creator_id': user_id,
                            "description": form.description.data,
                            'datetime': get_datetime(),
                            'on_kafka': True,  # TODO change if MQTT is available
                            'key': 'demokey'}]

            conn.execute(query, values_list)
            engine.dispose()
            # Create keyfile based on the given information
            create_keyfile(name=form_name, system_name=system_name)
            msg = "A client application with name '{}' was registered for the system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("client_app.show_client",
                                system_url=encode_sys_url(system_name), client_name=form_name))
        else:
            engine.dispose()
            msg = "The client with name '{}' was already created for system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("client_app.add_client", system_url=encode_sys_url(system_name)))

    return render_template("/client_apps/add_client.html", form=form, payload=payload)


# Delete client
@client_app.route("/delete_client/<string:system_url>/<string:client_name>", methods=["GET"])
@is_logged_in
def delete_client(system_url, client_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT clients.system_name, clients.name, agent.id AS agent_id
    FROM client_apps AS clients
    INNER JOIN is_admin_of_sys AS agf ON clients.system_name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}' AND clients.system_name='{}';""".format(user_id, system_name)
    result_proxy = conn.execute(query)
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an agent
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("client_app.show_all_clients"))

    # Check if the current user is agent of the system
    if user_id not in [c["agent_id"] for c in clients]:
        engine.dispose()
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("client_app.show_client",
                                system_url=encode_sys_url(system_name), client_name=client_name))

    # Delete the specified client
    query = """DELETE FROM client_apps AS clients
        WHERE system_name='{}' AND name='{}';""".format(system_name, client_name)
    conn.execute(query)
    engine.dispose()

    msg = f"The client '{client_name}' of the system '{system_name}' was deleted."
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))


# download key as zip
@client_app.route("/download_key/<string:system_url>/<string:client_name>", methods=["GET"])
@is_logged_in
def download_key(system_url, client_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Only the creator of an client is allowed to download the key
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT clients.system_name, name, creator.email AS contact_mail, creator_id
    FROM client_apps AS clients
    INNER JOIN users as creator ON creator.id=clients.creator_id
    WHERE creator_id='{}' AND system_name='{}';""".format(user_id, system_name)
    result_proxy = conn.execute(query)
    engine.dispose()
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an admin
    if len(clients) == 0:
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("client_app.show_all_clients"))

    # Check if the current user is agent of the system
    if user_id != clients[0]["creator_uuid"]:
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("client_app.show_client",
                                system_url=encode_sys_url(system_name), client_name=client_name))

    zipname = "ssl_{}_{}.zip".format(system_name, client_name)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(dir_path, "keys", zipname)

    if not os.path.exists(filepath):
        flash("The key file was not found.", "danger")
        return redirect(url_for("client_app.show_client",
                                system_url=encode_sys_url(system_name), client_name=client_name))

    # Set the status to download in order to flash a message in client.show_client
    if session.get("key_status") == "download":
        return redirect(url_for("client_app.show_client",
                                system_url=encode_sys_url(system_name), client_name=client_name))
    # This Session value must be reset there!
    session["key_status"] = "download"

    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()  # no transactions as they aren't threadsafe
    query = """UPDATE client_apps 
    SET keyfile_av=False
    WHERE name='{}' AND system_name='{}';""".format(client_name, system_name)
    result_proxy = conn.execute(query)
    engine.dispose()

    flash("The key was downloaded. Keep in mind that this key can't' be downloaded twice!", "success")
    return send_file(
        filepath,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename=zipname)
    # and redirect(url_for("client_app.show_client", system_uuid=system_uuid, client_name=client_name))

