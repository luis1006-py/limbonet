from fastapi import APIRouter, HTTPException, Header, Query, Response
from prometheus_client import Counter, generate_latest
from pydantic import BaseModel
import os, re, subprocess, base64, json
from typing import Optional
import datetime, sqlite3, ipaddress

with open ("./data/config.json", "r") as f:
	datos = json.load(f)

ALLOWED_COMMANDS = ["ACTUALIZAR_DNS", "LIMPIAR_CACHE"]
TEMP_DIR = datos["TEMP_DIR"]
lease_file = datos["DHCP_LEASES"]

def load_memory():
	with open("./data/memory.json", "r") as f:
		return json.load(f)

def save_memory(data):
	with open("./data/memory.json", "w") as f:
		json.dump(data, f, indent=4)

ubicaciones = {
	"TMP": datos["TEMP_DIR"],
	"DHCP": datos["DHCP_DIR"],
	"DNS": datos["DNS_DIR"],
	"NETPLAN": datos["NETPLAN_DIR"]
}

dhcp_file = os.path.join(ubicaciones["DHCP"], "dhcpd.conf")

def parse_dhcpd_conf(path=dhcp_file):
	with open(path, "r") as f:
		content = f.read()
	subnet_regex = re.finditer(
		r"subnet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(\d+\.\d+\.\d+\.\d+)\s*\{(.*?)\}",
		content, re.S)
	result = {}
	for match in subnet_regex:
		subnet_ip = match.group(1)
		mask = match.group(2)
		body = match.group(3)

		cidr = ipaddress.IPv4Network(
			f"{subnet_ip}/{mask}", strict=False
		)
		range_match = re.search(
			r"range\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+);", body
		)

		if not range_match:
			continue

		start_ip = range_match.group(1)
		end_ip = range_match.group(2)
		result[str(cidr)] = {
			"range": [start_ip, end_ip]
		}
	return result

def updateSubnet():
	subnets = parse_dhcpd_conf()
	memory = load_memory()
	memory["dhcp"]["last_restart"] = datetime.datetime.now().isoformat()
	memory["dhcp"]["subnets"] = subnets
	save_memory(memory)

router = APIRouter()

def verify_api_key(x_api_key: str = Header(...)):
	if x_api_key != datos["api_key"]:
		raise HTTPException(status_code=401, detail="Unauthorized")

class CommandPayload(BaseModel):
	data: str
	filename: Optional[str] = None
	#timestamp: float

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
					updateSubnet()

				elif accion == "updatenetplan":
					subprocess.run(['sudo', 'netplan', 'apply'], check=True)
					resultados.append("Netplan restarted")

			else:
				resultados.append("Unknown.")
	
	return ";".join(resultados)

@router.post("/recv")
def recv(payload: CommandPayload, x_api_key: str = Header(...)):
	verify_api_key(x_api_key)
	#if not hasattr(payload, "timestamp") or abs(datetime.datetime.now(datetime.timezone.utc).timestamp() - payload.timestamp) > 30:
	#	raise HTTPException(status_code=400, detail="Ha ocurrido un error") #Replay detectado o timestamp inválido
	
	try:
		# Si es un archivo
		if payload.filename:
			safe_name = os.path.basename(payload.filename) # Evitar que el nombre sea ..\..\..\y tal
			path = os.path.join(TEMP_DIR, safe_name)

			file_bytes = base64.b64decode(payload.data)

			with open(path, "wb") as f:
				f.write(file_bytes)
			resultado = f"ARCHIVO {safe_name} GUARDADO"
		else:
			comando = payload.data
			resultado = procesar(comando) # o ejecutar_comando(comando)

		return {
			"data": resultado
		}

	except Exception as e:
		#print(e) # Para debug
		raise HTTPException(status_code=500, detail=str(e))
	
@router.get("/updatedhcp")
def updatedhcp():
	memory = load_memory()
	stat = os.stat(lease_file)
	if memory["dhcp"]["inode"] != stat.st_ino:
		memory["dhcp"]["offset"] = 0
		memory["dhcp"]["inode"] = stat.st_ino

	conn = sqlite3.connect("logsSV.db")
	c = conn.cursor()

	inserted = 0

	with open(lease_file, "r") as f:
		f.seek(memory["dhcp"]["offset"])

		block = []
		while True:
			line = f.readline()
			if not line:
				break
			block.append(line)
			if line.strip() == "}":
				text = "".join(block)
				ip = re.search(r"lease\s+(\d+\.\d+\.\d+\.\d+)", text)
				mac = re.search(r"hardware ethernet (.*?);", text)
				hostname = re.search(r"(?:client-hostname|option host-name)\s+\"([^\"]+)\"", text)
				starts = re.search(r"starts \d+ (.*?);", text)
				ends = re.search(r"ends \d+ (.*?);", text)
				cltt = re.search(r"cltt \d+ (.*?);", text)
				binding = re.search(r"binding state (.*?);", text)

				if ip and mac:
					c.execute("""
					INSERT OR IGNORE INTO DHCP
					(
						ip,
						starts,
						ends,
						cltt,
						binding_state,
						hardware_ethernet,
			   			hostname,
						data
					)
					VALUES (?, ?, ?, ?, ?, ?, ?, ?)
					""", (
						ip.group(1),
						starts.group(1) if starts else None,
						ends.group(1) if ends else None,
						cltt.group(1) if cltt else None,
						binding.group(1) if binding else None,
						mac.group(1),
						hostname.group(1) if hostname else None,
						text
					))
					inserted += 1

				block = []
				memory["dhcp"]["offset"] = f.tell()
	conn.commit()
	conn.close()
	with open("data/memory.json", "w") as f:
		json.dump(memory, f, indent=4)
	return {
		"status": "ok",
		"inserted": inserted,
		"offset": memory["dhcp"]["offset"]
	}

@router.get("/dhcplogs")
def dhcplogs(
	ethernet: str = Query(None),
	ip: str = Query(None),
	x_api_key: str = Header(...)
):
	verify_api_key(x_api_key)
	conn = sqlite3.connect("logsSV.db")
	conn.row_factory = sqlite3.Row
	cursor = conn.cursor()

	query = """
		SELECT id, ip, starts, ends, cltt, binding_state, hardware_ethernet, hostname, data FROM DHCP WHERE 1=1
	"""
	params = []

	if ip:
		query += " AND ip LIKE ?"
		params.append(f'%{ip}%')
	if ethernet:
		ethernet = ethernet.lower().replace("-", ":")
		query += " AND lower(hardware_ethernet) LIKE ?"
		params.append(f"%{ethernet}%")
	query += " ORDER BY starts DESC LIMIT 100"
	cursor.execute(query, params)
	resultados = [dict (row) for row in cursor.fetchall()]
	conn.close()
	return resultados

@router.get("/metrics")
def metrics():
	return Response(generate_latest(), media_type="text/plain")

@router.get("/subnets")
def subnet_status():
	updateSubnet() #temporal luego eliminarlo
	memory = load_memory()
	subnets = memory["dhcp"]["subnets"]

	conn = sqlite3.connect("logsSV.db")
	cursor = conn.cursor()

	query = """
		SELECT ip, binding_state
		FROM DHCP
		WHERE id IN (
			SELECT MAX(id)
			FROM DHCP
			GROUP BY ip
		)
	"""
	cursor.execute(query)
	leases = cursor.fetchall()
	result = []

	for subnet_cidr, data in subnets.items():
		start_ip, end_ip = data["range"]
		start_int = int(ipaddress.ip_address(start_ip))
		end_int = int(ipaddress.ip_address(end_ip))
		total = end_int - start_int + 1
		used = 0
		for ip, state in leases:
			if state != "active":
				continue
			ip_int = int(ipaddress.ip_address(ip))
			if start_int <= ip_int <= end_int:
				used += 1
		result.append({
			"subnet": subnet_cidr,
			"total": total,
			"used": used,
			"free": total-used
		})
	conn.close()
	return result

# Fin del fichero