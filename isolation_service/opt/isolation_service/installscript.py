import sqlite3, re, json, urllib.request

def crear_bd_controllers():
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

def crear_base_de_datos():
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

def create_db():
	conn = sqlite3.connect("logsSV.db")
	c = conn.cursor()
	c.execute("""
		CREATE TABLE IF NOT EXISTS DHCP (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			ip TEXT NOT NULL,
			starts TEXT,
			ends TEXT,
			cltt TEXT,
			binding_state TEXT,
			hardware_ethernet TEXT,
			hostname TEXT,
			data TEXT,
			UNIQUE(ip, starts, ends, hardware_ethernet)
			)
		""")
	c.execute("CREATE INDEX IF NOT EXISTS idx_dhcp_ip ON DHCP(ip)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_dhcp_hardware ON DHCP(hardware_ethernet)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_dhcp_starts ON DHCP(starts)")
	conn.commit()
	conn.close()

def update_oui():
	txt=urllib.request.urlopen("https://standards-oui.ieee.org/oui/oui.txt").read().decode()
 
	db={
		m.group(1).replace("-",""):m.group(2).strip()
		for m in re.finditer(
			r"^([0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2})\s+\(hex\)\s+(.+)$",
			txt, re.M
		)
	}
 
	with open("./data/oui.json","w",encoding="utf-8") as f:
		json.dump(db,f,ensure_ascii=False,separators=(",",":"))

if __name__ == "__main__":
	crear_bd_controllers()
	crear_base_de_datos()
	create_db()
	update_oui()
