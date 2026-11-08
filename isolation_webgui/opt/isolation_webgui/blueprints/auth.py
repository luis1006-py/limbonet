from flask import Blueprint, render_template, redirect, url_for, session, flash
import sqlite3, os
from bcrypt import checkpw
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
#from werkzeug.exceptions import TooManyRequests

limiter = Limiter(key_func=get_remote_address)

from .forms import LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

def obtener_usuario(usuario):
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	cursor.execute("SELECT Idusuario, usuario, contraseña, rol FROM usuarios WHERE usuario = ?", (usuario,))
	datos = cursor.fetchone()
	conn.close()
	return datos

def safename(username): # Evitar sorpresitas como que el usuario sea ..\..\
	return username.replace("/", "_").replace("\\", "_").replace("..", "_")

@auth_bp.route("/inicio", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def lasdogin():
	form = LoginForm()

	if form.validate_on_submit():
		user = form.usuario.data
		pwd = form.contraseña.data
		datos = obtener_usuario(user)

		if datos and pwd:
			_id, usuario, contraseña_hash, rol = datos
			if checkpw(pwd.encode(), contraseña_hash):
				session.clear()
				session["usuario"] = usuario
				session["rol"] = rol
				flash("Login successful", "success")
				os.makedirs("./output/" + safename(session["usuario"]), exist_ok=True)

				return redirect(url_for("panel.panel_home"))
		flash("Incorrect username or password", "danger")
	return render_template("login1.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
	form = LoginForm()

	if form.validate_on_submit():
		user = form.usuario.data
		pwd = form.contraseña.data
		datos = obtener_usuario(user)

		if datos and pwd:
			_id, usuario, contraseña_hash, rol = datos
			if checkpw(pwd.encode(), contraseña_hash):
				session.clear()
				session["usuario"] = usuario
				session["rol"] = rol
				flash("Login successful", "success")
				os.makedirs("./output/" + safename(session["usuario"]), exist_ok=True)

				return redirect(url_for("panel.panel_home"))
		flash("Incorrect username or password", "danger")
	return render_template("login.html", form=form)

@auth_bp.route("/logout")
def logout():
	session.clear()
	#flash("Sesión cerrada", "info") No se va a mostrar si redirige a home
	return redirect(url_for("home"))