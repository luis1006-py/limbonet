from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, current_app
from functools import wraps
from modules.dhcp import formatDHCP, subnet as crear_subnet, reserva as crear_reserva, claseMAC, claseID, pool
import sqlite3, requests, re, json

dhcp_bp = Blueprint("dhcp", __name__, url_prefix="/dhcp")

def obtener_api(id_dispo):
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	cursor.execute("SELECT api_key FROM dispositivos WHERE Iddispo = ?", (id_dispo,))
	row = cursor.fetchone()
	conn.close()
	if row:
		return row[0]
	return ''

def login_required_dhcp(f):
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

@dhcp_bp.route("/")
@login_required_dhcp
def dhcp_home():
	return render_template("dhcp/dhcp_home.html")

@dhcp_bp.route("/vaciar")
@login_required_dhcp
def vaciar_config():
	formatDHCP(session["usuario"])
	flash("Configuration file emptied", "success")
	return redirect(url_for("dhcp.dhcp_home"))

@dhcp_bp.route("/subnet", methods=["GET", "POST"])
@login_required_dhcp
def subnet():
	if request.method == "POST":
		red = request.form.get("red")
		mascara = request.form.get("mascara")
		rango1 = request.form.get("rango1")
		rango2 = request.form.get("rango2")
		dns1 = request.form.get("dns1")
		dns2 = request.form.get("dns2")
		dnsname = request.form.get("dnsname")
		subnetmask = request.form.get("subnetmask")
		dg = request.form.get("dg")
		broadcast = request.form.get("broadcast")
		lease = request.form.get("lease")
		maxlease = request.form.get("maxlease")
		# Función de subnet pero sin el IN exactamente
		# session["usuario"]
		with open("./output/"+ session["usuario"] + "/dhcpd.conf", "a") as f:
			f.write(crear_subnet(red, mascara, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease)+'}\n')
		flash(f"Subnet received:", "info")
		return redirect(url_for("dhcp.dhcp_home"))
	return render_template("dhcp/dhcp_subnet.html")

@dhcp_bp.route("/reserva", methods=["GET", "POST"])
@login_required_dhcp
def reserva_dhcp():
	if request.method == "POST":
		name = request.form.get("name")
		mac = request.form.get("mac")
		ip = request.form.get("ip")
		dns1 = request.form.get("dns1")
		dns2 = request.form.get("dns2")
		dg = request.form.get("dg")
		with open("./output/"+ session["usuario"] + "/dhcpd.conf", "a") as f:
			f.write(crear_reserva(name, mac, ip, dns1, dns2, dg) +"\n")
		flash("Reservation added to dhcpd.conf", "success")
		return redirect(url_for("dhcp.dhcp_home"))
	return render_template("dhcp/dhcp_reserva.html")

@dhcp_bp.route("/clase", methods=["GET", "POST"])
@login_required_dhcp
def clase_dhcp():
	if request.method == "POST":
		tipo = request.form.get("tipo")
		nameclass = request.form.get("nameclass")

		if tipo == "id":
			id_value = request.form.get("id")
			texto_clase = claseID(nameclass, id_value)
		elif tipo == "mac":
			mac_value = request.form.get("mac")
			mac_option = request.form.get("macOption")
			if mac_option == "start":
				regla = "1"
			else: # mac_option == "end"
				regla = "2"
			texto_clase = claseMAC(nameclass, mac_value, regla)
		else:
			flash("Invalid rule type", "danger")
			return redirect(url_for("dhcp.clase"))
		
		with open("./output/"+ session["usuario"] + "/dhcpd.conf", "a") as f:
			f.write(texto_clase + "\n")
		
		flash("Class rule added", "success")
		return redirect(url_for("dhcp.dhcp_home"))
	return render_template("dhcp/dhcp_clase.html")

@dhcp_bp.route("/pool", methods=["GET", "POST"])
@login_required_dhcp
def pool_dhcp():
	if request.method == "POST":
		red = request.form.get("red")
		mascara = request.form.get("mascara")
		rango1 = request.form.get("rango1")
		rango2 = request.form.get("rango2")
		dns1 = request.form.get("dns1")
		dns2 = request.form.get("dns2")
		dnsname = request.form.get("dnsname")
		subnetmask = request.form.get("subnetmask")
		dg = request.form.get("dg")
		broadcast = request.form.get("broadcast")
		lease = request.form.get("lease")
		maxlease = request.form.get("maxlease")

		with open("./output/"+ session["usuario"] + "/dhcpd.conf", "a") as f: # SIN el } final
			f.write(crear_subnet(red, mascara, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease))

		# --- Clases dentro del pool ---
		clase_nombres = request.form.getlist("clase_nombre[]")
		clase_acciones = request.form.getlist("clase_accion[]")
		clase_rango1 = request.form.getlist("clase_rango1[]")
		clase_rango2 = request.form.getlist("clase_rango2[]")
		clase_dns1 = request.form.getlist("clase_dns1[]")
		clase_dns2 = request.form.getlist("clase_dns2[]")
		clase_dnsname = request.form.getlist("clase_dnsname[]")
		clase_subnetmask = request.form.getlist("clase_subnetmask[]")
		clase_dg = request.form.getlist("clase_dg[]")
		clase_broadcast = request.form.getlist("clase_broadcast[]")
		clase_lease = request.form.getlist("clase_lease[]")
		clase_maxlease = request.form.getlist("clase_maxlease[]")

		with open("./output/"+ session["usuario"] + "/dhcpd.conf", "a") as f:
			for i in range(len(clase_nombres)):
				f.write(pool(
					clase_acciones[i],
					clase_nombres[i],
					clase_rango1[i],
					clase_rango2[i],
					clase_dns1[i],
					clase_dns2[i],
					clase_dnsname[i],
					clase_subnetmask[i],
					clase_dg[i],
					clase_broadcast[i],
					clase_lease[i],
					clase_maxlease[i]
				))
			f.write("}\n")

		flash("Pool and classess added successfully", "success")
		return redirect(url_for("dhcp.dhcp_home"))
	return render_template("dhcp/dhcp_pool.html")

def obtenerResultadosLocal(LEASE_FILE, ethernet: str = None, ip: str = None, limit: int = 100):
	resultados = []

	with open(LEASE_FILE, "r") as f:
		block = []
		for line in f:
			block.append(line)

			if line.strip() == "}":
				text = "".join(block)
				block = []

				ip_m = re.search(r"lease\s+(\d+\.\d+\.\d+\.\d+)", text)
				mac = re.search(r"hardware ethernet (.*?);", text)
				hostname = re.search(r"(?:client-hostname|option host-name)\s+\"([^\"]+)\"", text)
				starts = re.search(r"starts \d+ (.*?);", text)
				ends = re.search(r"ends \d+ (.*?);", text)
				cltt = re.search(r"cltt \d+ (.*?);", text)
				binding = re.search(r"binding state (.*?);", text)
				if not ip_m or not mac:
					continue

				ip_val = ip_m.group(1)
				mac_val = mac.group(1).lower()

				if ip and ip not in ip_val:
					continue

				if ethernet:
					eth = ethernet.lower().replace("-", ":")
					if eth not in mac_val:
						continue

				resultados.append({
					"id": None,
					"ip": ip_val,
					"hardware_ethernet": mac_val,
					"hostname": hostname.group(1) if hostname else None,
					"starts": starts.group(1) if starts else None,
					"ends": ends.group(1) if ends else None,
					"cltt": cltt.group(1) if cltt else None,
					"binding_state": binding.group(1) if binding else None,
					"data": text
				})

	resultados.reverse()

	return resultados[:limit] 

@dhcp_bp.route("/logs", methods=["GET", "POST"])
@login_required_dhcp
def logs_dhcp():
	rol = session.get("rol")
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	if rol == 4:
		cursor.execute("""
			SELECT iddispo, hostname, ip FROM dispositivos
		""")
	else:
		cursor.execute("""
			SELECT d.iddispo, d.hostname, d.ip FROM dispositivos d
			JOIN permisos p ON p.id_dispositivo = d.iddispo
			JOIN usuarios u ON u.Idusuario = p.id_usuario
			WHERE u.usuario = ? AND p.permiso = 1
		""", (session["usuario"],))
	servidores = cursor.fetchall()
	conn.close()
	resultados =None
	marcas=None
	dispos= None

	if request.method == "POST":
		destino = request.form.get("destino")
		if rol == 4:
			# Admin obtiene la IP directamente
			conn = sqlite3.connect("database.db")
			cursor = conn.cursor()
			cursor.execute("SELECT ip FROM dispositivos WHERE iddispo = ?", (destino,))
			row = cursor.fetchone()
			conn.close()
			if not row:
				flash("Server not found.", "danger")
				return redirect(url_for("panel.panel_home"))
			ip_cliente = row[0]
			laapi = obtener_api(destino)
		else:
			# Usuario normal valida permisos
			conn = sqlite3.connect("database.db")
			cursor = conn.cursor()
			cursor.execute("""
				SELECT d.ip
				FROM dispositivos d
				JOIN permisos p ON p.id_dispositivo = d.iddispo
				JOIN usuarios u ON u.Idusuario = p.id_usuario
				WHERE u.usuario = ? AND p.permiso = 1 AND d.iddispo = ?
			""", (session["usuario"], destino))
			row = cursor.fetchone()
			conn.close()
			if not row:
				flash("Unauthorized attempt to access a server.", "danger")
				return redirect(url_for("panel.panel_home"))
			ip_cliente = row[0]

		if not ip_cliente == "local":
			ethernet = request.form.get("ethernet")
			ip = request.form.get("ip")
			try:
				conn = sqlite3.connect("database.db")
				cursor = conn.cursor()
				cursor.execute("""
					SELECT ip FROM dispositivos WHERE iddispo = ?
				""", (destino,))
				row = cursor.fetchone()
				conn.close()
				if not row:
					flash("Server not found", "danger")
					return redirect(url_for("dhcp.dhcp_logs"))
				ip_cliente = row[0]
				laapi = obtener_api(destino)
				headers = {
					"X-API-KEY": laapi
				}
				params = {}
				if ethernet:
					params["ethernet"] = ethernet
				if ip:
					params["ip"] = ip
				r = requests.get(
				f"{current_app.config['PROT']}://{ip_cliente}:{current_app.config['PORTC']}/dhcplogs",
					headers=headers,
					params=params,
					timeout=5
				)
				r.raise_for_status()
				resultados = r.json()
				r = requests.get(
					f"{current_app.config['PROT']}://{ip_cliente}:{current_app.config['PORTC']}/devices",
					timeout=5
				)
				r.raise_for_status()
				marcas = r.json()
				r = requests.get(
					f"{current_app.config['PROT']}://{ip_cliente}:{current_app.config['PORTC']}/subnets",
					timeout=5
				)
				r.raise_for_status()
				dispos = r.json()
			except Exception as e:
				flash(f"Error: {e}", "danger")
		else: # es Local
			ethernet = request.form.get("ethernet")
			ip = request.form.get("ip")
			resultados = obtenerResultadosLocal(current_app.config["LEASE_FILE"], ethernet, ip)
	print (dispos)
	return render_template("dhcp/dhcp_logs.html", servidores=servidores, resultados=resultados, marcas=marcas, dispos=dispos)

# Fin del archivo