from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from functools import wraps
from modules.dns import vaciarDNS, zonaDirecta, configBD, addRegister

dns_bp = Blueprint("dns", __name__, url_prefix="/dns")

def login_required_dns(f):
	@wraps(f)
	def wrapped(*args, **kwargs):
		if "usuario" not in session:
			flash("You must log in to access this page", "danger")
			return redirect(url_for("auth.login"))
		if session.get("rol", 0) > 3:
			pass
		else:
			abort(403) # Acceso denegado
		return f(*args, **kwargs)
	return wrapped

@dns_bp.route("/")
@login_required_dns
def dns_home():
	return render_template("dns/dns_home.html")

@dns_bp.route("/vaciar")
@login_required_dns
def vaciar_config():
	vaciarDNS()
	flash("Configuration file emptied", "success")
	return redirect(url_for("dns.dns_home"))

@dns_bp.route("/zonadirecta", methods=["GET", "POST"])
@login_required_dns
def zona_directa_dns():
	if request.method == "POST":
		name = request.form.get("name")
		db = request.form.get("db")
		with open("./output/"+ session["usuario"] + "/named.conf.local", "a") as f:
			f.write(zonaDirecta(name, db))
		flash("Forward zone created succesasfully", "success")
		return redirect(url_for("dns.dns_home"))
	return render_template("dns/dns_zonadirecta.html")

@dns_bp.route("/zonainversa", methods=["GET", "POST"])
@login_required_dns
def zona_inversa_dns():
	if request.method == "POST":
		name = request.form.get("in_addr_arpa")
		db = request.form.get("db")
		with open("./output/"+ session["usuario"] + "/named.conf.local", "a") as f:
			f.write(zonaDirecta(name, db)) # no es inversa porque automáticamente pone in-addr aqui lo hace del lado del cliente
		flash("Reverse zone created succesasfully", "success")
		return redirect(url_for("dns.dns_home"))
	return render_template("dns/dns_zonainversa.html")

@dns_bp.route("/configurarbd", methods=["GET", "POST"])
@login_required_dns
def configurar_bd_dns():
	if request.method == "POST":
		bdname = request.form.get("bdname")
		MNAME = request.form.get("MNAME") or "localhost."
		contact = request.form.get("contact") or "root.localhost."
		TTL = request.form.get("TTL") or "86400"
		serial = request.form.get("serial") or "1"
		refresh = request.form.get("refresh") or "604800"
		retry = request.form.get("retry") or "86400"
		expire = request.form.get("expire") or "2419200"
		negativeCacheTTL = request.form.get("negativeCacheTTL") or "86400"
		nameserver = request.form.get("nameserver") or "localhost."
		dirIP = request.form.get("dirIP") or None

		config_content = configBD(MNAME, contact, TTL, serial, refresh, retry, expire, negativeCacheTTL, nameserver, dirIP)

		with open(f"./output/{session['usuario']}/{bdname}", "w") as f:
			f.write(config_content)
		
		flash("Database configured successfully", "success")
		return redirect(url_for("dns.dns_home"))
	return render_template("dns/dns_configurarbd.html")

@dns_bp.route("/asignarregistros", methods=["GET", "POST"])
@login_required_dns
def asignar_registros_dns():
	if request.method == "POST":
		bdname = request.form.get("bdname")

		try:
			with open(f"./output/{session['usuario']}/{bdname}.conf", "r"):
				pass  # Si el archivo existe
		except FileNotFoundError:
			flash("Database does not exist.", "error")
			return redirect(url_for("dns.dns_home"))

		
		datos = request.form.getlist("dato[]")
		registros = request.form.getlist("register[]")
		valores = request.form.getlist("value[]")

		
		with open(f"./output/{session['usuario']}/{bdname}.conf", "a") as f:
			for dato, register, value in zip(datos, registros, valores):
				f.write(addRegister(dato, register, value))

		flash("Records addedd successfully.", "success")
		return redirect(url_for("dns.dns_home"))
	
	return render_template("dns/dns_asignarregistros.html")