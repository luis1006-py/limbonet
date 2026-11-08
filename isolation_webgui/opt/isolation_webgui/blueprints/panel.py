from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, abort
import sqlite3, base64, requests, socket, os, shutil, socket, json, re, subprocess
from bcrypt import hashpw, gensalt
from datetime import datetime
from .forms import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo
from functools import wraps

panel_bp = Blueprint("panel", __name__, url_prefix="/panel")

with open ("./config/localconfig.json", "r") as f:
	datos = json.load(f)

ALLOWED_COMMANDS = ["ACTUALIZAR_DNS", "LIMPIAR_CACHE"]
TEMP_DIR = datos["TEMP_DIR"]

ubicaciones = {
	"TMP": datos["TEMP_DIR"],
	"DHCP": datos["DHCP_DIR"],
	"DNS": datos["DNS_DIR"],
	"NETPLAN": datos["NETPLAN_DIR"],
	"DHCP_LEASES": datos["DHCP_LEASES"]
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

def verificarConexion(ip, puerto=1234, timeout=4):
	puerto = current_app.config['PORTC']
	try:
		with socket.create_connection((ip, puerto), timeout=timeout):
			return True
	except (socket.timeout, socket.error):
		return False

def login_required(rol_minimo=0):
	def decorator(f):
		@wraps(f)
		def wrapped(*args, **kwargs):
			if "usuario" not in session:
				flash("You must log in to access this page", "danger")
				return redirect(url_for("auth.login"))
			if session.get("rol", 0) >= rol_minimo:
				pass
			else:
				abort(403) # Acceso denegado
			return f(*args, **kwargs)
		return wrapped
	return decorator

class cambiarContraseña(FlaskForm):
	usuario = StringField("Usuario")
	contraseña = PasswordField("Nueva contraseña", validators=[DataRequired(), Length(min=3)])
	submit = SubmitField("Cambiar contraseña")

@panel_bp.route("/", methods=["GET", "POST"])
@login_required(rol_minimo=0)
def panel_home():
	if session['rol'] >= 3:
		admin = True
	else:
		admin = False
	método = "get"
	if request.method == "POST":
		método = "post"
		usuario = request.form.get("usuario")
		servidor = request.form.get("servidor")
		fecha = request.form.get("fecha")

		query = "SELECT * FROM logs WHERE 1=1"
		params = []

		if usuario:
			query += " AND user LIKE ?"
			params.append(f"%{usuario}%")
		if servidor:
			query += " AND sv = ?"
			params.append(servidor)
		if fecha:
			query += " AND date LIKE ?"
			params.append(f"%{fecha}%")
		conexion = sqlite3.connect("logs.db")
		cursor = conexion.cursor()
		cursor.execute(query, params)
		logs = cursor.fetchall()
		conexion.close()

		if logs:
			conexion_db = sqlite3.connect("database.db")
			cursor_db = conexion_db.cursor()
			logs = [list(log) for log in logs]

			for i, log in enumerate(logs):
				cursor_db.execute("SELECT ip FROM dispositivos WHERE Iddispo = ?", (log[2],))
				ip = cursor_db.fetchone()

				log.append(ip[0] if ip else "IP no encontrada")
			conexion_db.close()
	else:
		logs = []
	return render_template("panel.html", admin=admin, logs=logs, metodo=método)

@panel_bp.route("/change_password", methods=["GET", "POST"])
@login_required(rol_minimo=0)
def change_password():
	form = cambiarContraseña()
	# Admin puede cambiar todas las contraseñas
	if session.get("rol") != 4:
		form.usuario.data = session["usuario"]

	if form.validate_on_submit():
		usuario_obj = (form.usuario.data or "").strip() #Para que no me flagee errores
		nueva_clave = (form.contraseña.data or "").strip() #Para que no me flagee errores

		if session.get("rol") != 1:
			usuario_obj = session["usuario"]

		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()

		# Verificar que el usuario exista
		cursor.execute("SELECT idusuario FROM usuarios WHERE usuario = ?", (usuario_obj,))
		datos = cursor.fetchone()
		if not datos:
			flash("User not found", "danger")
			conn.close()
			return redirect(url_for("panel.change_password"))
		
		# Hashing nueva contraseña
		nueva_hash = hashpw(nueva_clave.encode("utf-8"), gensalt())
		cursor.execute("UPDATE usuarios SET contraseña = ? WHERE usuario = ?", (nueva_hash, usuario_obj))
		conn.commit()
		conn.close()

		flash(f"Password changed to {usuario_obj}", "success")
		return redirect(url_for("panel.panel_home"))
	return render_template("cambiar_contraseña.html", form=form)

class FormularioRegistroUsuario(FlaskForm):
	nombre_usuario = StringField("Nombre de Usuario", validators=[DataRequired(), Length(min=4, max=30)])
	contraseña = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6)])
	confirmar_contraseña = PasswordField("Confirmar Contraseña", validators=[DataRequired(), EqualTo('contraseña', message="Las contraseñas deben coincidir.")])
	rol = SelectField("Rol", choices=[(1, "TIER I"), (2, "TIER II"), (3, "TIER III")], coerce=int)
	submit = SubmitField("Crear Usuario")

@panel_bp.route("/crear_usuario", methods=["GET", "POST"])
@login_required(rol_minimo=4)  # Verifica que el rol del usuario sea 4 o mayor
def crear_usuario():
	form = FormularioRegistroUsuario()
	if form.validate_on_submit():
		nombre_usuario = (form.nombre_usuario.data or "").strip() # Para que no me flagee errores
		contraseña = (form.contraseña.data or "").strip() # Para que no me flagee errores
		rol = form.rol.data
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()
		cursor.execute("SELECT idusuario FROM usuarios WHERE usuario = ?", (nombre_usuario,))
		datos_usuario = cursor.fetchone()
		if datos_usuario:
			flash("Username already registered.", "danger")
			conn.close()
			return redirect(url_for("panel.crear_usuario"))
		hashed_password = hashpw(contraseña.encode('utf-8'), gensalt())
		cursor.execute("INSERT INTO usuarios (usuario, contraseña, rol) VALUES (?, ?, ?)", (nombre_usuario, hashed_password, rol))
		conn.commit()
		conn.close()
		flash("User created successfully", "success")
		return redirect(url_for("panel.panel_home"))
	return render_template("crear_usuario.html", form=form)

@panel_bp.route("/borrar_usuario", methods=["GET", "POST"])
@login_required(rol_minimo=4)
def borrar_usuario():
	if request.method == "POST":
		usuario = request.form.get("usuario")
		if usuario == "admin":
			flash("Cannot delete admin user", "danger")
			return redirect(url_for("panel.borrar_usuario"))
		elif not usuario:
			flash("No valid username received", "danger")
			return redirect(url_for("panel.borrar_usuario"))
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()
		cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,))
		conn.commit()

		if cursor.rowcount == 0:
			flash(f"User '{usuario}' does not exist", "danger")
		else:
			flash(f"User '{usuario}' has been deleted", "success")
		conn.close()
		carpeta_usuario = os.path.join('./output', usuario)  # ruta completa de la carpeta
		if os.path.exists(carpeta_usuario) and os.path.isdir(carpeta_usuario):
			shutil.rmtree(carpeta_usuario)
		return redirect(url_for("panel.borrar_usuario"))
	
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	cursor.execute("SELECT usuario FROM usuarios WHERE usuario != 'admin'")
	usuarios = cursor.fetchall()
	conn.close()
	return render_template("borrar_usuario.html", usuarios=usuarios)

@panel_bp.route("/vincular", methods=["GET", "POST"])
@login_required(rol_minimo=3)
def vincular():
	if request.method == "POST":
		ip = request.form.get("ip", "").strip()
		api_key = request.form.get("api_key", "").strip()
		if not ip or not api_key:
			flash("You must enter an IP address and/or API KEY", "danger")
			return redirect(url_for("panel.vincular"))
		
		try:
			url = f"{current_app.config['PROT']}://{ip}:{current_app.config['PORTC']}/hostname"
			headers = {"X-API-KEY": api_key}
			response = requests.post(url, headers=headers, timeout=4)
			
			response.raise_for_status()
			data = response.json()

			if data.get("status") != "OK":
				flash("Incorrect password", "danger")
				return redirect(url_for("panel.vincular"))
			hostname = data["hostname"]
		except Exception as e:
			flash(f"Could not obtain hostname: {e}", "danger")
			return redirect(url_for("panel.panel_home"))
		
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()

		cursor.execute("SELECT iddispo FROM dispositivos WHERE ip = ?", (ip,))
		row = cursor.fetchone()
		if row:
			conn.close()
			flash(f"The server with IP {ip} is already registered.", "warning")
			return redirect(url_for("panel.vincular"))

		cursor.execute(""" INSERT INTO dispositivos (hostname, ip, api_key) VALUES (?, ?, ?)""", (hostname, ip, api_key))
		conn.commit()
		conn.close()
		flash(f"Device linked: {hostname} ({ip})", "success")
		return redirect(url_for("panel.panel_home"))
	# para GET:
	return render_template("vincular.html")

def obtener_api(id_dispo):
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	cursor.execute("SELECT api_key FROM dispositivos WHERE Iddispo = ?", (id_dispo,))
	row = cursor.fetchone()
	conn.close()
	if row:
		return row[0]
	return ''

@panel_bp.route("/desvincular", methods=["GET", "POST"])
@login_required(rol_minimo=4)
def desvincular():
	if request.method == "POST":
		id_dispo = request.form.get("dispositivo")
		
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()
		cursor.execute("SELECT Iddispo, ip, api_key FROM dispositivos WHERE Iddispo = ?", (id_dispo,))
		dispositivo = cursor.fetchone()

		if not dispositivo:
			flash(f"The device with ID '{id_dispo}' does not exist", "danger")
			conn.close()
			return redirect(url_for("panel.desvincular"))

		id_dispo_db, ip, api_key = dispositivo

		try:
			ip_flask = socket.gethostbyname(socket.gethostname())
			url = f"{current_app.config['PROT']}://{ip}:{current_app.config['PORTC']}/remove-disp"
			headers = {"X-API-KEY": api_key}
			json_data = {"ip": ip_flask}
			response = requests.post(url, headers=headers, json=json_data, timeout=4)
			response.raise_for_status()

			# Eliminar el dispositivo de la base de datos
			cursor.execute("DELETE FROM dispositivos WHERE Iddispo = ?", (id_dispo,))
			conn.commit()

			flash(f"The device with ID '{id_dispo}' has been unlinked", "success")
			conn.close()
			return redirect(url_for("panel.desvincular"))
		except Exception as e:
			flash(f"The device could not be deleted on the server: {e}", "warning")
			return redirect(url_for("panel.desvincular"))


	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()
	cursor.execute("SELECT Iddispo, hostname FROM dispositivos")
	dispositivos = cursor.fetchall()
	conn.close()
	return render_template("desvincular.html", dispositivos=dispositivos)

@panel_bp.route("/modificar_permiso", methods=["GET", "POST"])
@login_required(rol_minimo=4)
def modificar_permiso():
	if request.method == "POST":
		id_usuario = int(request.form.get("id_usuario", 0))
		id_dispositivo = int(request.form.get("id_dispositivo", 0))
		permiso = int(request.form.get("permiso", 0))
		if permiso not in [0, 1, 2]:
			flash("Invalid permission", "danger")
			return redirect(url_for("panel.modificar_permiso"))
		
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()

		cursor.execute("SELECT Idusuario FROM usuarios WHERE Idusuario = ?", (id_usuario,))
		if not cursor.fetchone():
			flash("User not found", "danger")
			conn.close()
			return redirect(url_for("panel.modificar_permiso"))
		
		cursor.execute("SELECT Iddispo FROM dispositivos WHERE Iddispo = ?", (id_dispositivo,))
		if not cursor.fetchone():
			flash("Device not found", "danger")
			conn.close()
			return redirect(url_for("panel.modificar_permiso"))
		
		cursor.execute("""
				INSERT INTO permisos (id_usuario, id_dispositivo, permiso)
				VALUES (?, ?, ?)
				ON CONFLICT(id_usuario, id_dispositivo)
				DO UPDATE SET permiso=excluded.permiso
			""", (id_usuario, id_dispositivo, permiso))
		
		conn.commit()
		conn.close()

		flash("Permission modified successfully", "sucess")
		return redirect(url_for("panel.panel_home"))

	return render_template("modificar_permiso.html")

@panel_bp.route("/buscar", methods=["GET", "POST"])
@login_required(rol_minimo=3)
def buscar():
	if request.method == "POST":
		tipo_busqueda = request.form.get("tipo_busqueda")
		valor_busqueda = request.form.get("valor_busqueda")
		if not tipo_busqueda or not valor_busqueda:
			flash("You must enter a search type and value.", "danger")
			return redirect(url_for("panel.buscar"))

		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()

		if tipo_busqueda == "usuario":
			cursor.execute("SELECT Idusuario, usuario FROM usuarios WHERE usuario LIKE ?", ('%' + valor_busqueda + '%',))
			resultados = cursor.fetchall()
		elif tipo_busqueda == "dispositivo":
			cursor.execute("SELECT IDdispo, hostname, ip FROM dispositivos WHERE hostname LIKE ?", ('%' + valor_busqueda + '%',))
			resultados = cursor.fetchall()
		else:
			resultados = []

		conn.close()
		return render_template("buscar.html", resultados=resultados, tipo_busqueda=tipo_busqueda)
	return render_template("buscar.html", resultados=[], tipo_busqueda="")

def guardar_log(comando, destino, usuario, fichero=None):
	fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	conexion = sqlite3.connect("logs.db")
	cursor = conexion.cursor()
	cursor.execute("""
		INSERT INTO logs (user, sv, command, date, file)
		VALUES (?, ?, ?, ?, ?)

	""", (usuario, destino, comando, fecha, fichero))
	conexion.commit()
	conexion.close()

@panel_bp.route("/send_data", methods=["GET", "POST"])
@login_required(rol_minimo=0)
def send_data():
	rol = session.get("rol")
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	if rol == 4:
		cursor.execute("SELECT iddispo, hostname, ip FROM dispositivos")
	else:
		cursor.execute("""
			SELECT d.iddispo, d.hostname, d.ip
			FROM dispositivos d
			JOIN permisos p ON p.id_dispositivo = d.iddispo
			JOIN usuarios u ON u.Idusuario = p.id_usuario
			WHERE u.usuario = ? AND p.permiso = 2
		""", (session["usuario"],))
	servidores = cursor.fetchall()
	conn.close()
	
	if request.method == "POST":
		comando = request.form.get("comando", "TEMPLATE_COMANDO")
		destino = request.form.get("destino", "vacío")
		archivo = request.files.get("archivo")
			
		try:
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
					WHERE u.usuario = ? AND p.permiso = 2 AND d.iddispo = ?
				""", (session["usuario"], destino))
				row = cursor.fetchone()
				conn.close()
				if not row:
					flash("Unauthorized attempt to access a server.", "danger")
					return redirect(url_for("panel.panel_home"))
				ip_cliente = row[0]
				laapi = obtener_api(destino)
				
			if ip_cliente.lower() == "local": # Si su IP literal es "local" funciona de forma local
				resultado = procesar(comando)
				guardar_log(comando, destino, session["usuario"], None)
				flash(resultado, "success")
			else:
				print (ip_cliente)
				if archivo:
					archivo_bytes = archivo.read()
					#timestamp = datetime.now(timezone.utc).timestamp()
					payload_file = {
						"data": base64.b64encode(archivo_bytes).decode(),
						#"timestamp": timestamp,
						"filename": archivo.filename
					}
					headers = {"X-API-KEY": laapi}
					
					r_file = requests.post(f"{current_app.config['PROT']}://{ip_cliente}:{current_app.config['PORTC']}/recv", headers=headers, json=payload_file, timeout=10)
					r_file.raise_for_status()
					guardar_log(comando, destino, session["usuario"], archivo.filename)
					flash(f"File {archivo.filename} sent to {destino}.", "success")

				if comando:
					if comando.count(";") > 4:
						flash(f"No more than 4 commands can be sent", "danger")
						return redirect(url_for("panel.panel_home"))
					payload = {
						"data": comando,
						#"timestamp": timestamp
					}
					headers = {"X-API-KEY": laapi}
					r = requests.post(f"{current_app.config['PROT']}://{ip_cliente}:{current_app.config['PORTC']}/recv", headers=headers, json=payload, timeout=5)
					r.raise_for_status()
					resp_json = r.json()
					respuesta = resp_json["data"]
					guardar_log(comando, destino, session["usuario"], None)
					flash(f"Payload sent to {destino}, responds: {respuesta}", "success")

		except Exception as e:
			flash(f"Error sending payload to {destino}: {e}", "danger")
		return redirect(url_for("panel.panel_home"))
	return render_template("enviar_datos.html", servidores=servidores)
# Este es el finial del archivo