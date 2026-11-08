from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, abort
import json, os, sqlite3, requests, json, shutil, subprocess
from functools import wraps
from modules.netplancfg import configFichero

netplan_bp = Blueprint('netplan', __name__, url_prefix="/netplan")

def getInterfaces():
	try:
		interfaces = [
			name for name in (
			line.split(':')[1].split('@')[0].strip()
			for line in subprocess.check_output(['ip', '-o', 'link'], text=True).split('\n')
			if line
			)
			if name != "lo"
			]
		return interfaces
	except Exception as e:
		return ["error"]

def obtener_ip_servidor(destino):
	rol = session.get("rol")
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	
	if rol == 4:
		cursor.execute("SELECT ip FROM dispositivos WHERE iddispo = ?", (destino,))
	else:
		cursor.execute("""
			SELECT d.ip
			FROM dispositivos d
			JOIN permisos p ON p.id_dispositivo = d.iddispo
			JOIN usuarios u ON u.Idusuario = p.id_usuario
			WHERE u.usuario = ? AND p.permiso = 2 AND d.iddispo = ?
		""", (session["usuario"], destino))
	
	row = cursor.fetchone()
	conn.close()
	
	if not row:
		flash("Server not found or access denied.", "danger")
		return None
	return row[0]

def login_required_netplan(f):
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

@netplan_bp.route("/")
@login_required_netplan
def netplan_home():
	return render_template("netplan/netplan_home.html")

@netplan_bp.route("/vaciarnetplan", methods=["GET", "POST"])
@login_required_netplan
def vaciarnetplan():
	with open("./config/config.json", "r") as f:
		data = json.load(f)
	origen = data["netplan"]
	usuario = session["usuario"]
	output_dir = f"output/{usuario}"
	os.makedirs(output_dir, exist_ok=True)

	destino = os.path.join(output_dir, "netplan.yaml")
	shutil.copy(origen, destino)
	flash("Configuration file emptied", "success")
	return redirect(url_for("netplan.netplan_home"))

@netplan_bp.route('/configurarnetplan', methods=['GET', 'POST'])
@login_required_netplan
def configurarnetplan():
	if request.method == 'POST':
		servidor_id = request.form.get('servidor_id')
		if not servidor_id:
			flash("No server selected.", "danger")
			return redirect(url_for('netplan.configurarnetplan'))
		
		ip_servidor = obtener_ip_servidor(servidor_id)
		if not ip_servidor:
			return redirect(url_for('netplan.configurarnetplan'))
		
		try:
			if ip_servidor == "local":
				interfaces = getInterfaces()
			else:
				url = f"{current_app.config['PROT']}://{ip_servidor}:{current_app.config['PORTC']}/interfaces"
				res = requests.get(url, timeout=4)
				res.raise_for_status()
				data = res.json()
				interfaces = json.loads(data)
		except Exception as e:
			flash(f"An error has occurred: {e}", "danger")
			interfaces=[]
		return render_template("netplan/configurarnetplan.html", interfaces=interfaces, servidor_id=servidor_id)

	# GET
	rol = session.get('rol')
	destinos = []

	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	if rol == 4:
		cursor.execute("SELECT iddispo, ip FROM dispositivos")
	else:
		cursor.execute("""
			SELECT d.iddispo, d.ip
			FROM dispositivos d
			JOIN permisos p ON p.id_dispositivo = d.iddispo
			JOIN usuarios u ON u.Idusuario = p.id_usuario
			WHERE u.usuario = ? AND p.permiso = 2
		""", (session["usuario"],))
	destinos = cursor.fetchall()
	conn.close()
	
	return render_template("netplan/configurarnetplan.html", servidores=destinos)

@netplan_bp.route('/netplanconfigurado', methods=['POST'])
@login_required_netplan
def netplanconfigurado():
	servidor_id = request.form.get('servidor_id')

	if not servidor_id:
		flash("No server selected.", "danger")
		return redirect(url_for('netplan.configurarnetplan'))
	rol = session.get('rol')
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	if rol == 4:
		cursor.execute("SELECT ip FROM dispositivos WHERE iddispo = ?", (servidor_id,))
		row = cursor.fetchone()
		conn.close()
		if not row:
			flash("Server not found.", "danger")
			return redirect(url_for("netplan_bp.configurarnetplan"))
		ip_servidor = row[0]
	else:
		cursor.execute("""
			SELECT d.ip
			FROM dispositivos d
			JOIN permisos p ON p.id_dispositivo = d.iddispo
			JOIN usuarios u ON u.Idusuario = p.id_usuario
			WHERE u.usuario = ? AND p.permiso = 2 AND d.iddispo = ?
		""", (session["usuario"], servidor_id))
		row = cursor.fetchone()
		conn.close()
		if not row:
			flash("Unauthorized attempt to access a server.", "danger")
			return redirect(url_for("netplan_bp.configurarnetplan"))
		ip_servidor = row[0] 
	
	interfaces = request.form.getlist('interfaces')
	netplan_data = []

	for interface in interfaces:
		dhcp4 = request.form.get(f'dhcp4_{interfaces.index(interface)+1}') == 'on'
		ip = request.form.get(f'ip_{interfaces.index(interface)+1}')
		mask = request.form.get(f'mask_{interfaces.index(interface)+1}')
		dns1 = request.form.get(f'dns_primary_{interfaces.index(interface)+1}')
		dns2 = request.form.get(f'dns_secondary_{interfaces.index(interface)+1}')
		gateway = request.form.get(f'gateway_{interfaces.index(interface)+1}')

		if not dhcp4 and (not ip or not mask):
			flash(f"Please complete the IP address and subnet mask for {interface}.", "danger")
			continue

		netplan_data.append(configFichero([interface], dhcp4, ip, mask, gateway, dns1, dns2))

	user_dir = f"./output/{session['usuario']}"
	if not os.path.exists(user_dir):
		os.makedirs(user_dir)

	with open(f"{user_dir}/netplan.yaml", "a") as f:
		for data in netplan_data:
			f.write(data)
	flash("Network settings applied successfully.", "success")
	return redirect(url_for("netplan.configurarnetplan"))

@netplan_bp.route("/config-vlan", methods=['GET', 'POST'])
def config_vlan():
	if request.method == 'POST':
		iface_list = request.form.getlist("iface[]")
		vlan_id_list = request.form.getlist("vlan_id[]")
		ip_list = request.form.getlist("ip[]")
		dg_list = request.form.getlist("dg[]")
		dns_list = request.form.getlist('dns[]')

		user_dir = f"./output/{session['usuario']}"
		with open(f"{user_dir}/netplan.yaml", "a") as f:
			f.write(f"  vlans:\n")

			for idx, vlan_id in enumerate(vlan_id_list):
				if not vlan_id.isdigit() or not 1 <= int(vlan_id) <= 4094:
					flash(f"Incorrect VLAN ID {vlan_id}.", "danger")
					return redirect(url_for('netplan.config_vlan'))

				iface = iface_list[idx]
				ip = ip_list[idx]
				dg = dg_list[idx]
				dns = dns_list[idx] if dns_list[idx] else None

				f.write(f"    vlan{vlan_id}:\n")
				f.write(f"      id: {vlan_id}\n")
				f.write(f"      link: {iface}\n")
				f.write(f"      addresses: [{ip}]\n")
				f.write(f"      gateway4: {dg}\n")
				if dns:
					f.write(f"      nameservers:\n")
					f.write(f"        addresses: [{dns}]\n")
				else:
					f.write(f"      nameservers: []\n")

		flash("VLAN settings applied successfully.", "success")
		return redirect(url_for("netplan.netplan_home"))
	return render_template('netplan/config_vlan.html')
