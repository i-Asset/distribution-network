import sqlalchemy as db
from sqlalchemy import exc as sqlalchemy_exc

from flask import Blueprint, render_template, flash , redirect, url_for, session, request
from passlib.hash import sha256_crypt

from wtforms import Form, StringField, PasswordField, validators
from flask import current_app as app

from server.utils.useful_functions import get_id, is_logged_in

# print("current app: {}".format(app.config))
auth = Blueprint('auth', __name__) #, url_prefix='/comp')


# Register Form Class for the users
class RegisterForm(Form):
    first_name = StringField('First Name', [validators.DataRequired(),
                                            validators.Length(min=1, max=32)])
    name = StringField('Name', [validators.DataRequired(),
                                validators.Length(min=1, max=32)])
    email = StringField('Email', [validators.DataRequired(),
                                  validators.Email(message="The given email seems to be wrong.")])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match.')
    ])
    confirm = PasswordField('Confirm Password')


# Register user
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    email = form.email.data.strip()
    if request.method == 'POST' and form.validate():
        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = engine.connect()

        query = db.insert(app.config["tables"]["users"])
        new_id = get_id()
        values_list = [{'id': new_id,
                        'first_name': form.first_name.data.strip(),
                        'sur_name': form.name.data.strip(),
                        'email': email,
                        'password': sha256_crypt.hash(str(request.form["password"]), salt=str(abs(new_id)))}]
        try:
            ResultProxy = conn.execute(query, values_list)
            engine.dispose()
            app.logger.info("New registration: {}".format(values_list))
            flash("You are now registered and can log in.", "success")
            return redirect(url_for('auth.login'))

        except sqlalchemy_exc.IntegrityError:
            engine.dispose()
            flash("This email is already registered. Please log in.", "danger")
            return render_template('/auth/register.html', form=form)

    return render_template('/auth/register.html', form=form)


# User login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        email = request.form['email'].strip()
        password_candidate = request.form['password']

        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = engine.connect()

        query = "SELECT * FROM users WHERE email = '{}'".format(email)
        ResultProxy = conn.execute(query)
        results = ResultProxy.fetchall()
        engine.dispose()

        data = list()
        for row in results:
            data.append({results[0].keys()[i]: row[i] for i in range(0, len(row))})

        if len(data) == 0:
            error = 'Email not found.'
            return render_template('/auth/login.html', error=error)
        elif len(data) != 1:
            error = 'Username was found twice. Error'
            return render_template('login.html', error=error)
        else:
            password = data[0]['password']

            # Compare Passwords
            # if password == sha256_crypt.hash(password_candidate, salt=str(abs(data[0]["id"]))):
            if sha256_crypt.verify(password_candidate, hash=password):
                # Passed
                session['logged_in'] = True
                session['email'] = email
                session['user_id'] = data[0]['id']
                session['first_name'] = data[0]['first_name']
                session['sur_name'] = data[0]['sur_name']

                app.logger.info("New login: {}".format(email))
                flash('You are now logged in', 'success')
                return redirect(url_for('home.dashboard'))
            else:
                error = 'Invalid login.'
                app.logger.info("Invalid login: {}".format(email))
                return render_template('/auth/login.html', error=error)

    return render_template('/auth/login.html')


# User logout
@auth.route("/logout")
@is_logged_in
def logout():
    app.logger.info("New logout: {}".format(session['email']))
    session.clear()
    flash("You are now logged out.", "success")
    return redirect(url_for("auth.login"))
