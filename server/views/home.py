import logging
import os

import sqlalchemy as db
from flask import current_app as app, send_from_directory
from flask import Blueprint, render_template, flash, redirect, url_for, session, request

from .useful_functions import is_logged_in, strip_dict

home_bp = Blueprint("home", __name__)


@home_bp.route('/')
# @cache.cached(timeout=60)
def index():
    return redirect(url_for("home.dashboard"))


@home_bp.route("/dashboard")
def dashboard():
    # Redirect to home if not logged in
    if 'logged_in' not in session:
        return redirect(url_for("home.home"))

    # Get current user_id
    user_id = session["user_id"]

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # fetch name of user
    query = """SELECT first_name, sur_name FROM users WHERE id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    users = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    if users == list():
        flash("Please login.", "danger")
        return redirect(url_for("auth.login"))
    user = users[0]
    session["first_name"] = user["first_name"]
    session["sur_name"] = user["sur_name"]

    # fetch dedicated companies
    query = """SELECT com.id, name, domain, enterprise, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
    INNER JOIN users as admin ON admin.id=aof.user_id
    INNER JOIN users as creator ON creator.id=aof.creator_id
    WHERE admin.id='{}'
    ORDER BY name;""".format(user_id)
    result_proxy = conn.execute(query)
    companies = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched companies: {}".format(companies))

    # fetch dedicated systems
    query = """SELECT sys.name AS system_name, com.name AS com_name, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}'
    ORDER BY system_name;""".format(user_id)
    result_proxy = conn.execute(query)
    systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    # Fetch clients, for which systems the current user is agent of
    query = """SELECT client_apps.system_name AS system_name, client_apps.name AS client_name, creator.email AS contact_mail
    FROM client_apps
    INNER JOIN users as creator ON creator.id=client_apps.creator_id
    INNER JOIN systems AS sys ON client_apps.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}'
    ORDER BY system_name, client_apps.name;""".format(user_id)
    result_proxy = conn.execute(query)
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    # Fetch streams, for which systems the current user is agent of
    query = """
    SELECT streams.name, status, source_system, target_system, creator.email AS contact_mail
    FROM stream_apps as streams
    INNER JOIN users as creator ON creator.id=streams.creator_id
    INNER JOIN is_admin_of_sys AS agf ON streams.source_system=agf.system_name 
    WHERE agf.user_id='{}'
    ORDER BY source_system, target_system, streams.name;""".format(user_id)
    result_proxy = conn.execute(query)
    streams = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    engine.dispose()
    payload = dict()
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    return render_template("dashboard.html", companies=companies, systems=systems, clients=clients, streams=streams,
                           session=session, payload=payload)


@home_bp.route('/about')
def about():
    return render_template('about.html')


@home_bp.route('/home')
def home():
    payload = dict()
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    return render_template('home.html', payload=payload)


@home_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, "templates"),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@home_bp.route('/search', methods=['GET', 'POST'])
@is_logged_in
def search():
    search_request = request.args.get('request').strip().lower()
    app.logger.info("Searching for: {}".format(search_request))

    # Get current user_id
    user_id = session["user_id"]
    messages = dict()
    # msg_systems = msg_companies = msg_clients = msg_streamhub = None

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # fetch dedicated companies
    query = """SELECT company_id, com.*, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
    INNER JOIN users as admin ON admin.id=aof.user_id
    INNER JOIN users as creator ON creator.id=aof.creator_id
    WHERE admin.id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    companies = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    companies = [item for item in companies if search_request in str(list(item.values())).lower()]
    # print("Fetched companies: {}".format(companies))
    if companies == list():
        messages["companies"] = "No companies found."

    # fetch dedicated systems
    query = """SELECT domain, enterprise, sys.*, com.name AS company_name, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    systems = [item for item in systems if search_request in str(list(item.values())).lower()]
    if len(systems) == 0:
        messages["systems"] = "No systems found."

    # fetch dedicated clients
    query = """SELECT sys.name AS system_name, com.name AS company_name, client_apps.name, 
    domain, enterprise, workcenter, station, creator.email AS contact_mail, client_apps.*
    FROM client_apps
    INNER JOIN users as creator ON creator.id=client_apps.creator_id
    INNER JOIN systems AS sys ON client_apps.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    clients = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    clients = [item for item in clients if search_request in str(list(item.values())).lower()]
    if len(clients) == 0:
        messages["clients"] = "No clients found."

    # fetch dedicated aas
    query = """SELECT sys.name AS system_name, com.name AS company_name, aas.name, 
    domain, enterprise, workcenter, station, creator.email AS contact_mail, aas.*
    FROM aas
    INNER JOIN users as creator ON creator.id=aas.creator_id
    INNER JOIN systems AS sys ON aas.system_name=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    aas_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    aas_list = [item for item in aas_list if search_request in str(list(item.values())).lower()]
    if len(aas_list) == 0:
        messages["aas"] = "No aas found."

    # fetch dedicated streams
    query = """
    SELECT sys.name AS sys_name, creator.email AS contact_mail, stream_apps.*, com.name AS company_name
    FROM stream_apps
    INNER JOIN users as creator ON creator.id=stream_apps.creator_id
    INNER JOIN systems AS sys ON stream_apps.source_system=sys.name
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users as agent ON agent.id=agf.user_id
    WHERE agent.id='{}';""".format(user_id)
    result_proxy = conn.execute(query)
    streams = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    streams = [item for item in streams if search_request in str(list(item.values())).lower()]
    if len(streams) == 0:
        messages["streams"] = "No streams found."

    engine.dispose()
    found_count = len(companies) + len(systems) + len(clients) + len(streams)
    if found_count >= 1:
        flash("Received {} results for search request '{}'".format(found_count, search_request), "info")
    else:
        flash("Received no results for search request '{}'".format(found_count, search_request), "danger")
    return render_template("search.html", companies=companies, systems=systems, clients=clients, streams=streams,
                           messages=messages, search_request=search_request, aas_list=aas_list)
