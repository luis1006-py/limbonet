from fastapi import APIRouter, HTTPException, Header, Depends
import socket, json, sqlite3
from pydantic import BaseModel
from collections import Counter
import subprocess

router = APIRouter()
with open ("./data/config.json", "r") as f:
	datos = json.load(f)

def verify_api_key(x_api_key: str = Header(...)):
	if x_api_key != datos["api_key"]:
		raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/status")
def status():
	return {"status": "alive"}

@router.post("/hostname")
def get_hostname(api_key: str = Depends(verify_api_key)):
	hostname = socket.gethostname()
	ip = socket.gethostbyname(hostname)
	conn = sqlite3.connect("databaseSRV.db")
	cursor = conn.cursor()
	cursor.execute("INSERT OR REPLACE INTO controllers (id_dispositivo, ip) VALUES (?, ?)", (hostname, ip))
	conn.commit()
	conn.close()
	return {"status": "OK", "hostname": hostname}

class RemoveDeviceReq(BaseModel):
	ip: str

@router.post("/remove-disp")
def remove_disp(req: RemoveDeviceReq, api_key: str = Depends(verify_api_key)):
	ip_flask = req.ip
	try:
		conn = sqlite3.connect("databaseSRV.db")
		cursor = conn.cursor()
		cursor.execute("DELETE FROM controllers WHERE ip = ?", (ip_flask,))
		conn.commit()
		conn.close()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error al eliminar el dispositivo: {e}")
	return {"status": "OK", "message": f"Dispositivo eliminado correctamente"}

@router.get("/interfaces")
def interfaces(req: RemoveDeviceReq, api_key: str = Depends(verify_api_key)):
	try:
		interfaces = [
			name for name in (
			line.split(':')[1].split('@')[0].strip()
			for line in subprocess.check_output(['ip', '-o', 'link'], text=True).split('\n')
			if line
			)
			if name != "lo"
			]
		#interfaces = ["eth0", "wlan0", "docker0"]
		data = json.dumps(interfaces)
		return data
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

with open("./data/oui.json", "r", encoding="utf-8") as f:
	oui = json.load(f)

@router.get("/devices")
def get_devices():
	conn = sqlite3.connect("logsSV.db", check_same_thread=False)
	cur = conn.cursor()
	cur.execute("""
		SELECT hardware_ethernet
		FROM DHCP
		GROUP BY hardware_ethernet
	""")
	rows = cur.fetchall()
	conn.close()
	result = []
	counter = Counter()
	for (mac,) in rows:
		prefix = mac.replace(":", "").upper()[:6]
		vendor = oui.get(prefix, "Unknown")
		counter[vendor] += 1
	result = {}
	for vendor, total in counter.items():
		result[vendor] = total
	return result

# Fin del archivo