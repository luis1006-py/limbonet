from flask import Flask, render_template, abort
from blueprints import blueprints, blueprints_local
from flask_wtf.csrf import CSRFProtect
import json

with open ("./config/config.json", "r") as f:
	data = json.load(f)
with open ("./config/localconfig.json", "r") as f:
	datos = json.load(f)

app = Flask(__name__)
app.config["SECRET_KEY"] = data["SECRET_KEY"]
app.config["AES_KEY"] = bytes.fromhex(data["AES_KEY"])
app.config["PROT"] = data["PROT"]
app.config["PORTC"] = data["PORTC"]
app.config["LEASE_FILE"] = datos["DHCP_LEASES"]

if data["local"] == 0:
	app.config["LOCALMODE"] = False
	for bp in blueprints:
		app.register_blueprint(bp)
else:
	data["local"] = True
	for bp in blueprints_local:
		app.register_blueprint(bp)

csrf = CSRFProtect()
csrf.init_app(app)

@app.route("/")
def home():
	return render_template("index.html")

@app.route("/index")
def index():
	return render_template("home.html")
# Espero que no se desmaye el que vea esto

@app.route("/teapot")
def teapot():
	abort(418)

@app.route("/minecraft2")
def minecraft2():
	abort(451)

"""@app.errorhandler(400)
def bad_request(error):
	return render_template('400.html'), 400"""

@app.errorhandler(403)
def page_not_found(error):
	return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(error):
	return render_template('404.html'), 404

@app.errorhandler(405)
def method_not_allowed(error):
	return render_template('405.html'), 405

# HTTPS
'''
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(
	app.wsgi_app,
	x_for=1,
	x_proto=1,
	x_host=1,
	x_port=1
)

from flask import request, redirect
@app.before_request
def force_https():
	if not request.is_secure:
		return redirect(request.url.replace("http://", "https://"), code=301)

app.config.update(
	SESSION_COOKIE_SECURE=True,
	SESSION_COOKIE_HTTPONLY=True,
	SESSION_COOKIE_SAMESITE="Lax"
)
'''

if __name__ == '__main__':
	app.run(host="0.0.0.0", debug=True)