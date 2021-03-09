import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators, TextAreaField

from server.utils.useful_functions import get_datetime, get_id, is_logged_in, valid_level_name, strip_dict

company = Blueprint("company", __name__)  # url_prefix="/comp")


@company.route("/companies")
@is_logged_in
def show_all_companies():
    # Get current user_id
    user_id = session["user_id"]

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT com.id, domain, enterprise, com.name, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
    INNER JOIN users as admin ON admin.id=aof.user_id
    INNER JOIN users as creator ON creator.id=aof.creator_id
    WHERE admin.id='{}'
    ORDER BY domain, com;""".format(user_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    companies = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched companies: {}".format(companies))
    return render_template("/companies/companies.html", companies=companies)


@company.route("/show_company/<string:company_id>")
@is_logged_in
def show_company(company_id):
    # Get current user_id
    user_id = session["user_id"]

    # Set url (is used in system.delete_system)
    session["url"] = "/show_company/{}".format(company_id)

    # Fetch all admins for the requested company
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT com.id, com.name AS com_name, domain, enterprise, com.description, admin.id AS admin_id, 
    admin.first_name, admin.sur_name, admin.email, creator.email AS contact_mail, com.datetime AS com_datetime
    FROM companies AS com 
    INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
    INNER JOIN users as admin ON admin.id=aof.user_id 
    INNER JOIN users as creator ON creator.id=aof.creator_id 
    WHERE company_id='{}';""".format(company_id)
    result_proxy = conn.execute(query)
    admins = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched admins: {}".format(admins))

    # Check if the company exists and has admins
    if len(admins) == 0:
        engine.dispose()
        flash("It seems that this company doesn't exist.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # Check if the current user is admin of the company
    if user_id not in [c["admin_id"] for c in admins]:
        engine.dispose()
        flash("You are not permitted to see details of this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # if not, admins has at least one item
    payload = admins[0]

    # Fetch systems of this company
    query = """SELECT DISTINCT sys.name AS system_name, workcenter, station, com.name AS com_name, creator.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com on sys.company_id = com.id
    INNER JOIN is_admin_of_sys AS iaos on sys.name = iaos.system_name
    INNER JOIN users AS creator on iaos.creator_id = creator.id
     WHERE sys.company_id='{}';""".format(company_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    systems = [strip_dict(c.items()) for c in result_proxy.fetchall()]
    print(systems)

    return render_template("/companies/show_company.html", admins=admins, systems=systems, payload=payload)


# Company Form Class
class CompanyForm(Form):
    name = StringField("Full Company Name", [validators.Length(max=64)])
    domain = StringField("Domain", [validators.Length(min=1, max=5), valid_level_name])
    enterprise = StringField("Enterprise", [validators.Length(min=2, max=15), valid_level_name])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])


# Add company
@company.route("/add_company", methods=["GET", "POST"])
@is_logged_in
def add_company():
    # Get current user_id
    user_id = session["user_id"]
    # The basic company form is used
    form = CompanyForm(request.form)
    form.enterprise.label = "Enterprise short-name"
    form_name = form.name.data.strip()
    form_domain = form.domain.data.strip()
    form_enterprise = form.enterprise.data.strip()

    if request.method == "POST" and form.validate():
        # Create a new company and admin-relation using the form"s input
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()

        # Create company and check if the company_id or the company exists
        company_ids = ["init"]
        company_id = get_id()
        while company_ids != list():
            company_id = get_id()
            query = """SELECT id FROM companies WHERE id='{}';""".format(company_id)
            result_proxy = conn.execute(query)
            company_ids = result_proxy.fetchall()

        query = """SELECT domain, enterprise FROM companies 
                    WHERE domain='{}' AND enterprise='{}';""".format(form_domain, form_enterprise)
        result_proxy = conn.execute(query)
        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["companies"])
            values_list = [{"id": company_id,
                            "name": form_name,
                            "domain": form_domain,
                            "datetime": get_datetime(),
                            "enterprise": form_enterprise,
                            "description": form.description.data}]
            conn.execute(query, values_list)
        else:
            engine.dispose()
            flash("The company '{}.{}' already exists.".format(form_domain, form_enterprise), "danger")
            return redirect(url_for("company.show_all_companies"))

        # Create new is_admin_of_com instance
        query = db.insert(app.config["tables"]["is_admin_of_com"])
        values_list = [{"user_id": user_id,
                        "company_id": company_id,
                        "creator_id": user_id,
                        "datetime": get_datetime()}]
        try:
            conn.execute(query, values_list)
            engine.dispose()
            company_name = "{}.{}".format(form_domain, form_enterprise)
            app.logger.info(f"The company '{company_name}' was created by '{user_id}'.")
            flash("The company '{}' was created.".format(company_name), "success")
            return redirect(url_for("company.show_all_companies"))

        except sqlalchemy_exc.IntegrityError as e:
            engine.dispose()
            app.logger.error("An Integrity Error occured: {}".format(e))
            flash("An unexpected error occured.", "danger")
            return render_template(url_for("auth.login"))

    return render_template("/companies/add_company.html", form=form)


# Delete company
@company.route("/delete_company/<string:com_id>", methods=["GET"])
@is_logged_in
def delete_company(com_id):
    # Get current user_id
    user_id = session["user_id"]

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT com.id AS com_id, domain, enterprise, user_id
        FROM companies AS com 
        INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
        WHERE aof.user_id='{}'
        AND aof.company_id='{}';""".format(user_id, com_id)
    result_proxy = conn.execute(query)
    permitted_companies = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        engine.dispose()
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # Check if you are the last admin of the company
    query = """SELECT aof.company_id, domain, enterprise, user_id
        FROM companies AS com INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
        WHERE aof.company_id='{}';""".format(com_id)
    result_proxy_admin = conn.execute(query)

    # Check if there is no system left
    query = """SELECT sys.company_id
        FROM companies AS com 
        INNER JOIN systems AS sys ON com.id=sys.company_id 
        WHERE sys.company_id='{}';""".format(com_id)
    result_proxy_system = conn.execute(query)

    if len(result_proxy_system.fetchall()) >= 1:
        flash("You are not permitted to delete a company which has systems.", "danger")
        engine.dispose()
        return redirect(url_for("company.show_company", company_id=com_id))
    if len(result_proxy_admin.fetchall()) >= 2:
        flash("You are not permitted to delete a company which has other admins.", "danger")
        engine.dispose()
        return redirect(url_for("company.show_all_companies"))

    # Now the company can be deleted
    selected_company = permitted_companies[0]  # This list has only one element
    company_name = "{}.{}".format(selected_company["domain"], selected_company["enterprise"])

    transaction = conn.begin()
    try:
        # Delete new is_admin_of_com instance
        query = """DELETE FROM is_admin_of_com
            WHERE company_id='{}';""".format(com_id)
        conn.execute(query)
        # Delete company
        query = """DELETE FROM companies WHERE id='{}';""".format(com_id)
        conn.execute(query)
        transaction.commit()
        engine.dispose()

        app.logger.info("The company '{}' was deleted.".format(company_name))
        flash("The company '{}' was deleted.".format(company_name), "success")
    except:
        transaction.rollback()
        app.logger.warning("The company '{}' couldn't be deleted.".format(company_name))
        flash("The company '{}' couldn't be deleted.".format(company_name), "danger")
    finally:
        return redirect(url_for("company.show_all_companies"))


# Admin Management Form Class
class AdminForm(Form):
    email = StringField("Email", [validators.Email(message="The given email seems to be wrong.")])


@company.route("/add_admin_company/<string:company_id>", methods=["GET", "POST"])
@is_logged_in
def add_admin_company(company_id):
    # Get current user_id
    user_id = session["user_id"]

    form = AdminForm(request.form)

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT com.id AS com_id, name, domain, enterprise, creator.email AS contact_mail
            FROM companies AS com 
            INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
            INNER JOIN users as admin ON admin.id=aof.user_id
            INNER JOIN users as creator ON creator.id=aof.creator_id
            WHERE admin.id='{}' 
            AND com.id='{}';""".format(user_id, company_id)
    result_proxy = conn.execute(query)
    engine.dispose()
    permitted_companies = [strip_dict(c.items()) for c in result_proxy.fetchall() if str(c["com_id"]) == company_id]

    if permitted_companies == list():
        flash("You are not permitted to add an admin for this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    selected_company = permitted_companies[0]

    domain = selected_company["domain"]
    enterprise = selected_company["enterprise"]

    if request.method == "POST" and form.validate():
        email = form.email.data.strip()

        # Create cursor
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()

        # Check if the user is registered
        query = """SELECT id AS user_id FROM users WHERE email='{}';""".format(email)
        result_proxy = conn.execute(query)
        found_users = [strip_dict(c.items()) for c in result_proxy.fetchall()]

        if found_users == list():
            flash("No user was found with this email address.", "danger")
            return render_template("/companies/add_admin_company.html", form=form, domain=domain,
                                   enterprise=enterprise)

        user = found_users[0]
        # Check if the user is already admin of this company
        query = """SELECT com.id AS com_id, user_id
        FROM companies AS com 
        INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
        WHERE aof.user_id='{}' AND com.id='{}';""".format(user["user_id"], company_id)
        result_proxy = conn.execute(query)
        if result_proxy.fetchall() != list():
            engine.dispose()
            flash("This user is already admin of this company.", "danger")
            return render_template("/companies/add_admin_company.html", form=form, domain=domain,
                                   enterprise=enterprise)

        # Create new is_admin_of_com instance
        query = db.insert(app.config["tables"]["is_admin_of_com"])
        values_list = [{"user_id": user["user_id"],
                        "company_id": selected_company["com_id"],
                        "creator_id": user_id,
                        "datetime": get_datetime()}]

        conn.execute(query, values_list)
        engine.dispose()
        msg = "The user '{}' was added to '{}.{}' as an admin.".format(form.email.data, domain, enterprise)
        app.logger.info(msg)
        flash(msg, "success")
        return redirect(url_for("company.show_company", company_id=selected_company["com_id"]))

    return render_template("/companies/add_admin_company.html", form=form, domain=domain, enterprise=enterprise)


# Delete admin for company
@company.route("/delete_admin_company/<string:company_id>/<string:admin_id>", methods=["GET"])
@is_logged_in
def delete_admin_company(company_id, admin_id):
    # Get current user_id
    user_id = session["user_id"]

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT com.id AS com_id, domain, enterprise, creator.email AS contact_mail
        FROM companies AS com 
        INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
        INNER JOIN users as admin ON admin.id=aof.user_id
        INNER JOIN users as creator ON creator.id=aof.creator_id
        WHERE admin.id='{}'
        AND aof.company_id='{}';""".format(admin_id, company_id)
    result_proxy = conn.execute(query)
    permitted_companies = [strip_dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        engine.dispose()
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    elif str(user_id) == str(admin_id):
        engine.dispose()
        flash("You are not permitted to remove yourself.", "danger")
        return redirect(url_for("company.show_company", company_id=company_id))

    else:
        # get info for the deleted user
        query = """SELECT com.id AS com_id, domain, enterprise, admin.email AS admin_email, admin.id AS admin_id
                FROM companies AS com 
                INNER JOIN is_admin_of_com AS aof ON com.id=aof.company_id 
                INNER JOIN users as admin ON admin.id=aof.user_id
                WHERE admin.id='{}'
                AND aof.company_id='{}';""".format(admin_id, company_id)
        result_proxy = conn.execute(query)
        del_users = [strip_dict(c.items()) for c in result_proxy.fetchall()]
        if del_users == list():
            engine.dispose()
            flash("nothing to delete.", "danger")
            return redirect(url_for("company.show_all_companies"))

        else:
            del_user = del_users[0]
            # Delete new is_admin_of_com instance
            query = """DELETE FROM is_admin_of_com
                WHERE user_id='{}'
                AND company_id='{}';""".format(admin_id, company_id)
            conn.execute(query)
            # print("DELETING: {}".format(query))

            engine.dispose()

            msg = "The user with email '{}' was removed as admin from company '{}.{}'.".format(
                del_user["admin_email"], del_user["domain"].strip(), del_user["enterprise"].strip())
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("company.show_company", company_id=del_user["com_id"]))
