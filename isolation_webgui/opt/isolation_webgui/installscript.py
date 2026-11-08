import sqlite3, argparse
from bcrypt import hashpw, gensalt

def crearDBlogs():
	conexion = sqlite3.connect("logs.db")
	cursor = conexion.cursor()
	cursor.execute("""
		CREATE TABLE IF NOT EXISTS logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user TEXT NOT NULL,
			sv INTEGER NOT NULL,
			command TEXT NOT NULL,
			date TEXT NOT NULL,
			file TEXT
		)
	""")
	conexion.commit()
	conexion.close()
	print("Base de datos logs.db creada correctamente")

def crearDBservidor():
	conn = sqlite3.connect("databaseSRV.db")
	cursor = conn.cursor()

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS controllers (
			id_dispositivo TEXT PRIMARY KEY,
			ip TEXT NOT NULL
		)
	""")

	cursor.execute("""
		CREATE TABLE IF NOT EXISTS permisos (
			id_usuario INTEGER PRIMARY KEY,
			permiso INTEGER NOT NULL
		)
	""")

	conn.commit()
	conn.close()
	print("Base de datos databaseSRV.db creada correctamente")

def crearDBavanzada():
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS usuarios (
		Idusuario INTEGER PRIMARY KEY AUTOINCREMENT,
		usuario TEXT UNIQUE NOT NULL,
		contraseña TEXT NOT NULL,
		rol INTEGER NOT NULL
	);
	""")

	usuario = "admin"
	clave_plana = "admin"
	rol = 4

	clave_hash = hashpw(clave_plana.encode("utf-8"), gensalt())

	try:
		cursor.execute(
			"INSERT INTO usuarios (usuario, contraseña, rol) VALUES (?, ?, ?)",
			(usuario, clave_hash, rol)
		)
		print("Usuario admin creado.")
	except sqlite3.IntegrityError:
		print("El usuario admin ya existe.")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS dispositivos (
		Iddispo INTEGER PRIMARY KEY AUTOINCREMENT,
		hostname TEXT NOT NULL,
		ip TEXT NOT NULL,
		api_key TEXT NOT NULL
	);
	""")

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS permisos (
		id_usuario INTEGER NOT NULL,
		id_dispositivo INTEGER NOT NULL,
		permiso INTEGER NOT NULL DEFAULT 0,
		PRIMARY KEY (id_usuario, id_dispositivo),
		FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE ON UPDATE CASCADE,
		FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id) ON DELETE CASCADE ON UPDATE CASCADE
	);
	""")

	conn.commit()
	conn.close()
	print("Base de datos database.db creada correctamente")

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-mode", choices=["client", "server"])
	args = parser.parse_args()

	if args.mode == "client":
		crearDBavanzada()
		crearDBlogs()
	elif args.mode == "server":
		crearDBservidor()
	else:
		print ("Especificar -mode")

if __name__ == '__main__':
	main()