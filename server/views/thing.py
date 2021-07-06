import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from wtforms import Form, StringField, validators, TextAreaField

from server.utils.useful_functions import get_datetime, is_logged_in, valid_name, valid_url, strip_dict, \
    decode_sys_url, encode_sys_url

thing = Blueprint("thing", __name__)  # url_prefix="/thing")


@thing.route("/things")
@is_logged_in
def show_all_thing():
    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients, for which systems the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT things.system_name, things.name, things.resource_uri, creator.email AS contact_mail
    FROM things
    INNER JOIN is_admin_of_sys AS agf ON things.system_name=agf.system_name 
    INNER JOIN users as creator ON creator.id=agf.creator_id
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}'
    ORDER BY system_name, things.name;""".format(user_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    thing_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    return render_template("/things/things.html", thing_list=thing_list)


@thing.route("/show_thing/<string:system_url>/<string:thing_name>")
@is_logged_in
def show_thing(system_url, thing_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch all clients for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT things.system_name, com.name AS company_name, com.id AS company_id, things.name, things.resource_uri,
    creator.email AS contact_mail, things.description, agent.id AS agent_id, things.datetime AS datetime
    FROM things
    INNER JOIN users as creator ON creator.id=things.creator_id
    INNER JOIN systems AS sys ON things.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE sys.name='{}' AND things.name='{}';""".format(system_name, thing_name)
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
    config = {"thing_name": thing_name,
              "system_name": system_name,
              "resource_uri": payload.get("resource_uri", "")}

    return render_template("/things/show_thing.html", payload=payload, config=config)


# Client Form Class
class ThingForm(Form):
    name = StringField("Name of the thing connection", [validators.Length(min=2, max=20), valid_name])
    resource_uri = StringField("Resource URI", [valid_url])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])


# Add client in clients view, redirect to systems
@thing.route("/add_thing")
@is_logged_in
def add_thing():
    # redirect to systems
    flash("Specify the system to which a thing connection should be added.", "info")
    return redirect(url_for("system.show_all_systems"))


# Add client in system view
@thing.route("/add_thing/<string:system_url>", methods=["GET", "POST"])
@is_logged_in
def add_client_for_system(system_url):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # The basic client form is used
    form = ThingForm(request.form)
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
        FROM things
        WHERE system_name='{}' AND name='{}';""".format(system_name, form_name)
        result_proxy = conn.execute(query)

        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["things"])
            values_list = [{'name': form_name,
                            'system_name': system_name,
                            'resource_uri': form.resource_uri.data.strip(),
                            'creator_id': user_id,
                            "description": form.description.data,
                            'datetime': get_datetime()}]

            conn.execute(query, values_list)
            engine.dispose()

            msg = "A thing connection with name '{}' was registered for the system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("thing.show_thing",
                                system_url=encode_sys_url(system_name), thing_name=form_name))
        else:
            engine.dispose()
            msg = "The thing connection with name '{}' was already created for system '{}'.".format(form_name, system_name)
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("thing.add_thing", system_url=encode_sys_url(system_name)))

    return render_template("/things/add_thing.html", form=form, payload=payload)


# Delete client
@thing.route("/delete_thing/<string:system_url>/<string:thing_name>", methods=["GET"])
@is_logged_in
def delete_thing(system_url, thing_name):
    system_name = decode_sys_url(system_url)

    # Get current user_id
    user_id = session["user_id"]

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT things.system_name, things.name, agf.user_id AS agent_id
    FROM things
    INNER JOIN is_admin_of_sys AS agf ON things.system_name=agf.system_name
    WHERE agf.user_id='{}' AND things.system_name='{}';""".format(user_id, system_name)
    result_proxy = conn.execute(query)
    thing_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an agent
    if len(thing_list) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("thing.show_all_things"))

    # Check if the current user is agent of the system
    if user_id not in [c["agent_id"] for c in thing_list]:
        engine.dispose()
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("thing.show_thing",
                                system_url=encode_sys_url(system_name), thing_list=thing_list))

    # Delete the specified client
    query = """DELETE FROM things WHERE system_name='{}' AND name='{}';""".format(system_name, thing_name)
    conn.execute(query)
    engine.dispose()

    msg = f"The thing connection '{thing_name}' of the system '{system_name}' was deleted."
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
