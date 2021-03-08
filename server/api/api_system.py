import os
import zlib

import requests
import urllib
import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, jsonify

# Must be imported to use the app config
from flask import current_app as app
from passlib.hash import sha256_crypt

from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators, TextAreaField

from .api_auth import authorize_request
from ..utils.useful_functions import get_datetime, is_logged_in, valid_level_name, encode_sys_url, decode_sys_url, \
    strip_dict, safe_strip

prefix = "/distributionnetwork"  # url_prefix="/distributionnetwork/")
api_system = Blueprint("api_system", __name__)


@api_system.route(f"{prefix}", methods=['GET'])
def test_api():
    return jsonify({"value": "You are connected with the awesome distribution network."})


@api_system.route(f"{prefix}/systems_by_person", methods=['GET'])
def systems_by_person_no_id():
    return jsonify({"value": f"Please specify a personId/user_id: {prefix}/systems_by_person/<int:user_id>"})


@api_system.route(f"{prefix}/systems_by_person/<string:user_id>", methods=['GET'])
def systems_by_person(user_id):
    """
    Searches for all systems in the distribution network of which the user is admin of. The user_id must be
    authenticated on the identity-service.
    :param user_id: personId of the Identity-service, or (if negative) the user_id of the demo Digital Twin platform
    :return: Json of all found systems
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/systems_by_person/<string:user_id>"
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct, request=request)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # 2) Fetch all systems that belong to the user with id user_id
    # cases without authorization are returned, here the user is definitely permitted to request the data
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    result_proxy = conn.execute(f"""
    SELECT sys.name AS system_name, com.name AS company, sys.description,
    sys.datetime AS created_at, creator_id, creator.first_name, creator.sur_name, creator.email, sys.*,
    mqtt.server as mqtt_server, mqtt.version as mqtt_version, mqtt.topic as mqtt_topic
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_id=com.id
    INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name 
    INNER JOIN users AS agent ON agent.id=agf.user_id
    INNER JOIN users as creator ON creator.id=agf.creator_id 
    FULL JOIN mqtt_broker AS mqtt ON sys.name=mqtt.system_name 
    WHERE agf.user_id='{user_id}';""")
    engine.dispose()
    systems = [dict(c.items()) for c in result_proxy.fetchall()]

    # 3) Structure the raw data and return
    for i, res in enumerate(systems):
        sys = dict()
        res = {k: v for k, v in res.items() if v}
        for key in ["system_name", "created_at", "company", "description", "company_id", "kafka_server",
                    "company_id"]:
            sys[key] = safe_strip(res.get(key, ""))
        sys["creator"] = {"creator_id": res.get("creator_id", ""),
                          "first_name": res.get("first_name", ""),
                          "sur_name": res.get("sur_name", ""),
                          "email": res.get("email", "")}
        sys["mqtt_broker"] = {"mqtt_server": res.get("mqtt_server", ""),
                              "mqtt_version": res.get("mqtt_version", ""),
                              "mqtt_topic": res.get("mqtt_topic", "")}
        systems[i] = sys

    return jsonify({"systems": systems})


@api_system.route(f"{prefix}/create_system/<string:user_id>", methods=['POST'])
def systems_by_person_post(user_id):
    """
    Create a system by sending a json containing user, company and
    :return: return the system's name
    """
    # 1) extract the header content with the keys: Host, User-Agent, Accept, Authorization
    #    check if the user is allowed to get the systems (user_id < 0 -> Panta Rhei, user_id > 0 -> identity-service
    fct = f"{prefix}/create_system/<string:user_id>"
    authorized, msg, status_code = authorize_request(user_id=user_id, fct=fct, request=request)
    if not authorized:
        return jsonify({"value": msg, "url": fct, "status_code": status_code}), status_code

    # TODO insert new system here, also upload a user and company if necessary
    # fetch user with id
    # fetch company and check if the users it authorized to create a system
    # create the new system
    # return system
    print(request.json)
    return jsonify({"new system": request.json})


# @api_system.route("/systems")
# @is_logged_in
# def show_all_systems():
#     # Get current user_id
#     user_id = session["user_id"]
#
#     # Set url (is used in system.delete_system)
#     session["last_url"] = "/systems"
#
#     # Fetch systems, for which the current user is agent of
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT sys.name AS sys_name, com.name AS com_name, domain, enterprise, workcenter, station, agent.email AS contact_mail
#     FROM systems AS sys
#     INNER JOIN companies AS com ON sys.company_id=com.id
#     INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#     INNER JOIN users as agent ON agent.id=agf.user_id
#     WHERE agent.id='{}'
#     ORDER BY domain, com, workcenter, station;""".format(user_id)
#     result_proxy = conn.execute(query)
#     engine.dispose()
#     systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#     for sys in systems:
#         sys["sys_url"] = encode_sys_url(sys["sys_name"])
#     # print("Fetched companies: {}".format(companies))
#
#     return render_template("/systems/systems.html", systems=systems)

#
# @api_system.route("/show_system/<string:system_url>")
# @is_logged_in
# def show_system(system_url):
#     system_name = decode_sys_url(system_url)
#     # Get current user_id
#     user_id = session["user_id"]
#
#     # Fetch all agents for the requested system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """
#     SELECT sys.name AS system_name, com.name AS com_name, domain, enterprise, sys.description, workcenter, station, sys.datetime AS sys_datetime,
#     agent.id AS agent_id, agent.first_name, agent.sur_name, agent.email AS agent_mail, creator.email AS creator_mail
#     FROM systems AS sys
#     INNER JOIN companies AS com ON sys.company_id=com.id
#     INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#     INNER JOIN users as agent ON agent.id=agf.user_id
#     INNER JOIN users as creator ON creator.id=agf.creator_id
#     WHERE sys.name='{}';""".format(system_name)
#     result_proxy = conn.execute(query)
#     engine.dispose()
#     agents = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#     # print("Fetched agents: {}".format(agents))
#
#     # Check if the system exists and has agents
#     if len(agents) == 0:
#         engine.dispose()
#         flash("It seems that this system doesn't exist.", "danger")
#         return redirect(url_for("system.show_all_systems"))
#
#     # Check if the current user is agent of the system
#     if user_id not in [c["agent_id"] for c in agents]:
#         engine.dispose()
#         flash("You are not permitted see details this system.", "danger")
#         return redirect(url_for("system.show_all_systems"))
#
#     # Fetch client_apps of the system, for with the user is agent
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT client_apps.system_name, client_apps.name, creator.email AS contact_mail
#     FROM client_apps
#     INNER JOIN users as creator ON creator.id=client_apps.creator_id
#     INNER JOIN is_admin_of_sys AS agf ON client_apps.system_name=agf.system_name
#     WHERE agf.user_id='{}' AND agf.system_name='{}';""".format(user_id, system_name)
#     result_proxy = conn.execute(query)
#     # engine.dispose()
#     client_apps = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     # Fetch clients, for which systems the current user is agent of
#     query = """SELECT aas.system_name, aas.name, aas.registry_uri, creator.email AS contact_mail
#     FROM aas
#     INNER JOIN is_admin_of_sys AS agf ON aas.system_name=agf.system_name
#     INNER JOIN users as creator ON creator.id=agf.creator_id
#     INNER JOIN users as agent ON agent.id=agf.user_id
#     WHERE agent.id='{}'
#     ORDER BY system_name, aas.name;""".format(user_id)
#     result_proxy = conn.execute(query)
#     # engine.dispose()
#     aas_list = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     # Fetch streams, for which systems the current user is agent of
#     # engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     # conn = engine.connect()
#     query = """
#     SELECT sys.name AS system_name, stream_apps.name AS name, source_system, target_system, creator.email AS contact_mail
#     FROM stream_apps
#     INNER JOIN users as creator ON creator.id=stream_apps.creator_id
#     INNER JOIN systems AS sys ON stream_apps.source_system=sys.name
#     INNER JOIN companies AS com ON sys.company_id=com.id
#     INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#     INNER JOIN users as agent ON agent.id=agf.user_id
#     WHERE agent.id='{}' AND sys.name='{}';""".format(user_id, system_name)
#     result_proxy = conn.execute(query)
#     engine.dispose()
#     streams = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     # if not, agents has at least one item
#     payload = agents[0]
#     return render_template("/systems/show_system.html", agents=agents, payload=payload,
#                            client_apps=client_apps, streams=streams, aas_list=aas_list)
#
#
# # System Form Class
# class SystemForm(Form):
#     workcenter = StringField("Workcenter", [validators.Length(min=2, max=30), valid_level_name])
#     station = StringField("Station", [validators.Length(min=2, max=20), valid_level_name])
#     description = TextAreaField("Description", [validators.Length(max=16*1024)])
#
#
# # Add system in system view, redirect to companies
# @api_system.route("/add_system")
# @is_logged_in
# def add_system():
#     # redirect to companies
#     flash("Specify the company to which a system should be added.", "info")
#     return redirect(url_for("company.show_all_companies"))
#
#
# # Add system in company view
# @api_system.route("/add_system/<string:company_id>", methods=["GET", "POST"])
# @is_logged_in
# def add_system_for_company(company_id):
#     # Get current user_id
#     user_id = session["user_id"]
#
#     # The basic company form is used
#     form = SystemForm(request.form)
#     form.workcenter.label = "Workcenter short-name"
#     form_workcenter = form.workcenter.data.strip()
#     form_station = form.station.data.strip()
#
#     # Get payload
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """
#     SELECT company_id, com.name AS com_name, domain, enterprise, admin.id AS admin_id, admin.first_name, admin.sur_name, admin.email
#     FROM companies AS com
#     INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id
#     INNER JOIN users as admin ON admin.id=aof.user_id
#     INNER JOIN users as creator ON creator.id=aof.creator_id
#     WHERE company_id='{}';""".format(company_id)
#     result_proxy = conn.execute(query)
#     admins = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     # Check if the company exists and you are an admin
#     if len(admins) == 0:
#         engine.dispose()
#         app.logger.warning("It seems that the company with the id '{}' doesn't exist.".format(company_id))
#         flash("It seems that this company doesn't exist.", "danger")
#         return redirect(url_for("company.show_all_companies"))
#
#     # Check if the current user is admin of the company
#     if user_id not in [c["admin_id"] for c in admins]:
#         engine.dispose()
#         flash("You are not permitted to add systems for this company.", "danger")
#         return redirect(url_for("company.show_all_companies"))
#
#     # if not, admins has at least one item
#     payload = admins[0]
#
#     # Create a new system and agent-relation using the form"s input
#     if request.method == "POST" and form.validate():
#         # Create system and check if either the system_id or the system exists
#
#         query = """SELECT domain, enterprise FROM systems
#                 INNER JOIN companies ON systems.company_id=companies.id
#                 WHERE domain='{}' AND enterprise='{}' AND workcenter='{}' AND station='{}';
#                 """.format(payload["domain"], payload["enterprise"], form_workcenter, form_station)
#         result_proxy = conn.execute(query)
#         system_name = f'{payload["domain"].strip()}.{payload["enterprise"].strip()}.{form_workcenter}.{form_station}'
#         if len(result_proxy.fetchall()) == 0:
#             query = db.insert(app.config["tables"]["systems"])
#             values_list = [{"name": system_name,
#                             "company_id": payload["company_id"],
#                             "workcenter": form_workcenter,
#                             "station": form_station,
#                             "datetime": get_datetime(),
#                             "description": form.description.data}]
#             conn.execute(query, values_list)
#         else:
#             engine.dispose()
#             flash(f"The system {system_name} already exists.", "danger")
#             return redirect(url_for("company.show_company", company_id=company_id))
#
#         transaction = conn.begin()
#         try:
#             # Create new is_admin_of_sys instance
#             query = db.insert(app.config["tables"]["is_admin_of_sys"])
#             values_list = [{"user_id": user_id,
#                             "system_name": system_name,
#                             "creator_id": user_id,
#                             "datetime": get_datetime()}]
#             conn.execute(query, values_list)
#             engine.dispose()
#
#             # Create system topics
#             try:
#                 app.kafka_interface.create_system_topics(system_name=system_name)
#             except Exception as e:
#                 app.logger.warning(f"Couldn't create Kafka topics for system '{system_name}, {e}")
#
#             transaction.commit()
#             app.logger.info("The system '{}' was created.".format(system_name))
#             flash("The system '{}' was created.".format(system_name), "success")
#             return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#         except Exception as e:
#             transaction.rollback()
#             app.logger.warning("The system '{}' couldn't created.".format(system_name))
#             app.logger.debug("Error: {}".format(e))
#             flash("The system '{}' couldn't created.".format(system_name), "danger")
#             return render_template("/auth/login.html")
#
#     return render_template("systems/add_system.html", form=form, payload=payload)
#
#
# # Delete system
# @api_system.route("/delete_system/<string:system_url>", methods=["GET"])
# @is_logged_in
# def delete_system(system_url):
#     system_name = decode_sys_url(system_url)
#     # Get current user_id
#     user_id = session["user_id"]
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_id, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.id=sys.company_id
#         INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#         WHERE agf.user_id='{}'
#         AND agf.system_name='{}';""".format(user_id, system_name)
#     result_proxy = conn.execute(query)
#     permitted_systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         engine.dispose()
#         flash("You are not permitted to delete this system.", "danger")
#         return redirect(url_for("system.show_all_systems"))
#
#     # Check if you are the last agent of the system
#     query = """SELECT company_id, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.id=sys.company_id
#         INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#         AND agf.system_name='{}';""".format(system_name)
#     result_proxy = conn.execute(query)
#     agents = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#     if len(agents) >= 2:
#         engine.dispose()
#         flash("You are not permitted to delete a system which has multiple agents.", "danger")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#
#     # Check if there are client_apps, stream_apps or aas for that system
#     query = f"""(SELECT system_name, name, 'client apps'::varchar(16) AS type
#                 FROM client_apps WHERE system_name='{system_name}')
#         UNION
#             (SELECT source_system AS system_name, name, 'stream apps' FROM stream_apps WHERE source_system='{system_name}')
#         UNION
#             (SELECT system_name, name, 'aas' FROM aas WHERE system_name='{system_name}');"""
#     result_proxy = conn.execute(query)
#     dep_instances = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#     if len(dep_instances) >= 1:
#         engine.dispose()
#         # print(dep_instances)
#         dep_types = list(set([instance["type"] for instance in dep_instances]))
#         flash(f"You are not permitted to delete a system which has {', '.join(dep_types)}.", "danger")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#     # Check if there are client applications for that system
#
#     transaction = conn.begin()
#     # try:
#     # Delete single mqtt_broker
#     query = """DELETE FROM mqtt_broker
#         WHERE system_name='{}';""".format(system_name)
#     conn.execute(query)
#     # Delete is_admin_of_sys instance(s)
#     query = """DELETE FROM is_admin_of_sys
#         WHERE system_name='{}';""".format(system_name)
#     conn.execute(query)
#     # Delete single system
#     query = """DELETE FROM systems
#         WHERE name='{}';""".format(system_name)
#     conn.execute(query)
#     engine.dispose()
#
#     # Delete Kafka topics
#     if app.kafka_interface.delete_system_topics(system_name=system_name):
#         transaction.commit()
#         app.logger.info("The system '{}' was deleted.".format(system_name))
#         flash("The system '{}' was deleted.".format(system_name), "success")
#     else:
#         transaction.rollback()
#         app.logger.warning("The system '{}' couldn't be deleted, returned False".format(system_name))
#         flash("The system '{}' couldn't be deleted.".format(system_name), "danger")
#     # except:
#     #     transaction.rollback()
#     #     app.logger.warning("The system '{}' couldn't be deleted.".format(system_name))
#     #     flash("The system '{}' couldn't be deleted.".format(system_name), "danger")
#     # finally:
#     # Redirect to latest page, either /systems or /show_company/UID
#     if session.get("last_url"):
#         return redirect(session.get("last_url"))
#     return redirect(url_for("system.show_all_systems"))
#
#
# # Agent Management Form Class
# class AgentForm(Form):
#     email = StringField("Email", [validators.Email(message="The given email seems to be wrong.")])
#
#
# @api_system.route("/add_agent_system/<string:system_url>", methods=["GET", "POST"])
# @is_logged_in
# def add_agent_system(system_url):
#     system_name = decode_sys_url(system_url)
#     # Get current user_id
#     user_id = session["user_id"]
#
#     form = AgentForm(request.form)
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_id, system_name, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.id=sys.company_id
#         INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#         WHERE agf.user_id='{}'
#         AND agf.system_name='{}';""".format(user_id, system_name)
#     result_proxy = conn.execute(query)
#     permitted_systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         engine.dispose()
#         flash("You are not permitted to add an agent for this system.", "danger")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#
#     payload = permitted_systems[0]
#
#     if request.method == "POST" and form.validate():
#         email = form.email.data.strip()
#
#         # Check if the user is registered
#         query = """SELECT * FROM users WHERE email='{}';""".format(email)
#         result_proxy = conn.execute(query)
#         found_users = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#         if found_users == list():
#             engine.dispose()
#             flash("No user was found with this email address.", "danger")
#             return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
#         user = found_users[0]
#         # Check if the user is already agent of this system
#         query = """SELECT system_name, user_id FROM is_admin_of_sys
#         WHERE user_id='{}' AND system_name='{}';""".format(user["id"], system_name)
#         result_proxy = conn.execute(query)
#         if result_proxy.fetchall() != list():
#             engine.dispose()
#             flash("This user is already agent of this system.", "danger")
#             return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
#         # Create new is_admin_of_sys instance
#         query = db.insert(app.config["tables"]["is_admin_of_sys"])
#         values_list = [{"user_id": user["id"],
#                         "system_name": payload["system_name"],
#                         "creator_id": user_id,
#                         "datetime": get_datetime()}]
#         conn.execute(query, values_list)
#         engine.dispose()
#
#         flash("The user {} was added to {}.{}.{}.{} as an agent.".format(
#             email, payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]), "success")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#
#     return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
#
# # Delete agent for system
# @api_system.route("/delete_agent_system/<string:system_url>/<string:agent_id>", methods=["GET"])
# @is_logged_in
# def delete_agent_system(system_url, agent_id):
#     system_name = decode_sys_url(system_url)
#     # Get current user_id
#     user_id = session["user_id"]
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_id, system_name, domain, enterprise, workcenter, station
#             FROM companies AS com
#             INNER JOIN systems AS sys ON com.id=sys.company_id
#             INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#             WHERE agf.user_id='{}'
#             AND agf.system_name='{}';""".format(user_id, system_name)
#     result_proxy = conn.execute(query)
#     permitted_systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         engine.dispose()
#         flash("You are not permitted to delete agents for this system.", "danger")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#
#     if str(user_id) == str(agent_id):
#         engine.dispose()
#         flash("You can't remove yourself.", "danger")
#         return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
#
#     # get info for the deleted agent
#     query = """SELECT company_id, system_name, domain, enterprise, workcenter, station, agent.email AS email,
#     agent.id AS agent_id
#     FROM companies AS com
#     INNER JOIN systems AS sys ON com.id=sys.company_id
#     INNER JOIN is_admin_of_sys AS agf ON sys.name=agf.system_name
#     INNER JOIN users as agent ON agent.id=agf.user_id
#     WHERE agent.id='{}'
#     AND agf.system_name='{}';""".format(agent_id, system_name)
#     result_proxy = conn.execute(query)
#     del_users = [strip_dict(c.items()) for c in result_proxy.fetchall()]
#
#     if del_users == list():
#         engine.dispose()
#         flash("nothing to delete.", "danger")
#         return redirect(url_for("company.show_all_systems"))
#
#     del_user = del_users[0]
#     # Delete new is_admin_of_sys instance
#     query = """DELETE FROM is_admin_of_sys
#         WHERE user_id='{}'
#         AND system_name='{}';""".format(agent_id, system_name)
#     conn.execute(query)
#     # print("DELETING: {}".format(query))
#
#     engine.dispose()
#     flash("User with email {} was removed as agent from system {}.{}.{}.{}.".format(
#         del_user["email"], del_user["domain"], del_user["enterprise"], del_user["workcenter"], del_user["station"]),
#         "success")
#     return redirect(url_for("system.show_system", system_url=encode_sys_url(system_name)))
