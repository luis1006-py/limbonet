from flask import Blueprint, render_template, abort,  flash, redirect, url_for, abort, session
import json, re, subprocess, os, sqlite3
from functools import wraps

with open ("./config/localconfig.json", "r") as f:
	datos = json.load(f)

ALLOWED_COMMANDS = ["ACTUALIZAR_DNS", "LIMPIAR_CACHE"]
TEMP_DIR = datos["TEMP_DIR"]

ubicaciones = {
	"TMP": datos["TEMP_DIR"],
	"DHCP": datos["DHCP_DIR"],
	"DNS": datos["DNS_DIR"],
	"NETPLAN": datos["NETPLAN_DIR"]
}

def procesar(texto):
	# MOVER FICHERO "db.empty" A "DNS"
	# ELIMINAR FICHERO "db.empty" DE "TMP"
	patrones = {
		"mover": r'\bMOVER\b.*\bFICHERO\b\s*"([^"]+)"\s*\bA\b\s*"([^"]+)"',
		"eliminar": r'\bELIMINAR\b.*\bFICHERO\b\s*"([^"]+)"\s*\bDE\b\s*"([^"]+)"'
	}
	comandos = texto.split(";")
	resultados = []

	for comando in comandos:
		comando = comando.strip()
		if comando:
			for accion, patron in patrones.items():
				coincidencia = re.search(patron, comando, re.IGNORECASE)
				if coincidencia:
					fichero = coincidencia.group(1)
					destino_clave = coincidencia.group(2).upper() # Destino o directorio
					
					if accion == "mover":
						# Mover siempre desde TMP
						origen = os.path.join(ubicaciones["TMP"], fichero)
						if destino_clave not in ubicaciones:
							resultados.append(f"ERROR: El destino '{destino_clave}' no está definido.")
							break
						destino = ubicaciones[destino_clave]
						
						if not os.path.isfile(origen):
							resultados.append(f"ERROR: El archivo '{origen}' no existe.")
							break
						if os.path.isdir(destino):
							destino = os.path.join(destino, fichero)
						os.rename(origen, destino)
						resultados.append("HECHO")

					elif accion == "eliminar":
						# Eliminar solo archivos dentro de TMP
						ruta = os.path.join(ubicaciones["TMP"], fichero)
						
						if not os.path.exists(ruta):
							resultados.append(f"ERROR: El archivo '{ruta}' no existe.")
							break
						os.remove(ruta)
						resultados.append("HECHO")
					break

				elif accion == "updatebind":
					subprocess.run(['sudo', 'systemctl', 'restart', 'bind9'], check=True)
					resultados.append("BIND9 restarted")
				elif accion == "updatedhcp":
					subprocess.run(['sudo', 'systemctl', 'restart', 'isc-dhcp-server'], check=True)
					resultados.append("DHCP restarted")
				elif accion == "updatenetplan":
					subprocess.run(['sudo', 'netplan', 'apply'], check=True)
					resultados.append("Netplan restarted")
			else:
				resultados.append("Unknown.")
	
	return ";".join(resultados)

local_bp = Blueprint("local", __name__, url_prefix="/")

def login_required(f):
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

@local_bp.route("/localmode")
@login_required
def localmode():
	conn = sqlite3.connect('database.db')
	cursor = conn.cursor()
	cursor.execute("SELECT ip FROM dispositivos WHERE ip = ?", ('local',))
	dispositivo = cursor.fetchone()
	conn.close()
	if dispositivo:
		abort(404)
	return render_template('localmode.html')

@local_bp.route("/confirmlocal", methods=["POST"])
@login_required
def confirmlocal():
	conn = sqlite3.connect('database.db')
	cursor = conn.cursor()
	cursor.execute("SELECT Ip FROM dispositivos WHERE ip = ?", ('local',))
	dispositivo = cursor.fetchone()
	if dispositivo:
		conn.close()
		abort(404)
	cursor.execute("""
		INSERT INTO dispositivos (hostname, ip, api_key)
		VALUES(?, ?, ?)
	""", ('local', 'local', 'local',))
	conn.commit()
	conn.close()
	return "Local mode enabled."