from flask import Flask, request, redirect, make_response, render_template, url_for
from flask.json import jsonify
import os
import logging
import urllib.parse
import intents
from user import User, Query
import re, secrets


USER_VALIDATION = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if (re.search(USER_VALIDATION, username)):
            logging.debug(f"Username {username} is a valid email address.")
        else:
            error = 'Invalid username, must be an email address.'
            return render_template('login.html', error=error)
        user = User()
        try:
            sessionid = user.login(username, password)
            response = make_response(redirect(url_for('auth', _external=True, _scheme='https')))
            response.set_cookie('Session-ID', sessionid)
            logging.debug("Redirecting to auth.")
            return response
        except Exception as e:
            error = 'Invalid username or password.'
            return render_template('login.html', error=error)

    else:
        return render_template('login.html', error=error)



@app.route('/auth')
def auth():
    # Authentication endpoint from google.
    logging.debug("Request args: " + str(request.args))
    if 'Session-ID' in request.cookies:
        sessionid = request.cookies.get('Session-ID')
        user = User()
        user_info = user.check_session(sessionid)
        if user_info is not False:
            logging.debug("Session ID valid")
            redirect_uri = request.args.get('redirect_uri')
            authorization_code = make_token()
            docid = list(user_info[0].keys())[0]
            user.update(docid, {'authorization_code': authorization_code})
            payload = {
                'state': request.args.get('state'),
                'response_type': request.args.get('response_type'),
                'code': authorization_code
            }
            redirect_uri = redirect_uri + '?' + urllib.parse.urlencode(payload)
            return redirect(redirect_uri)
        else:
            logging.debug(f"SessionID not valid.")
            return redirect(url_for("login"))
    else:
        logging.debug("SessionID not set. Redirect to login.")
        return redirect(
            url_for("login", _scheme='https', _external=True)
        )


@app.route('/token', methods=['POST'])
def token():
    logging.debug('Request Form: ' + str(request.form))
    if request.form.get('grant_type') == 'authorization_code':
        authorization_code = request.form.get('code')
        logging.debug(f"Got authorization code, looking up: {authorization_code}")
        user = User()
        query = Query(
            field='authorization_code',
            op_string='==',
            value=authorization_code
        )
        auth_code_result = user.query(query)['results']
        if len(auth_code_result) < 1:
            response = make_response(jsonify(error="invalid_grant"), 400)
            return response
        else:
            docid = list(auth_code_result[0].keys())[0]
            logging.debug(f"Found docid: {docid}")
            access_token = make_token()
            refresh_token = make_token()
            logging.debug("Creating refresh and access tokens.")
            user.update(docid, data={
                'access_token': access_token,
                'refresh_token': refresh_token
            })
            payload = {
                "token_type": "Bearer",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": 3600
            }
    elif request.form.get('grant_type') == 'refresh_token':
        #Refresh request.
        refresh_token = request.form.get('refresh_token')
        user = User()
        query = Query(
            field='refresh_token',
            op_string='==',
            value=refresh_token
        )
        refresh_token_result = user.query(query)['results']
        if len(refresh_token_result) < 1:
            logging.debug(f"Invalid refresh token: {refresh_token_result}.")
            response = make_response(jsonify(error="invalid_grant"), status=400)
            return response

        docid = list(refresh_token_result[0].keys())[0]
        logging.debug(f"Updating token for: {docid}")
        access_token = make_token()
        user.update(docid, data={
            'access_token': access_token,
        })

        payload = {
            "token_type": "Bearer",
            "access_token": access_token,
            "expires_in": 3600
        }
    print('Response: ' + str(jsonify(payload)))
    return jsonify(payload)


@app.route('/smarthome', methods=['POST'])
def smarthome():
    logging.debug("Headers: " + str(request.headers))
    logging.debug("JSON: " + str(request.json))
    if 'Authorization' not in request.headers:
        response = make_response(jsonify(error="Unauthorized"), 400)
        return response

    access_token = request.headers.get("Authorization").replace("Bearer ", "")
    logging.debug(f"Smarthome request, authorization: {access_token}.")
    user = User()
    user_info = user.check_token(access_token)
    if user_info is False:
        response = make_response(jsonify(error="Unauthorized"), 400)
        return response
    docid = list(user_info[0].keys())[0]
    logging.debug(f"Authorized request as: {docid}")

    payload = request.json
    intent = intents.Intent(docid=docid)
    intent_status = intent.get(payload=payload)

    # TODO: Should return true, but if not, do something.

    logging.debug(f"RequestId: {intent.request_id}, Intent: {intent.intent}")
    intent_result = intent.run(intent.intent, payload)

    logging.debug(f"Intent result: {intent_result}")
    return jsonify(intent_result)


def make_token():
    """
    Creates a cryptographically-secure, URL-safe string
    """
    return secrets.token_urlsafe(36)