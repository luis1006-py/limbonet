import asyncio, time, smtplib, socket, psutil, datetime, json
from collections import deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from prometheus_client import Counter, Gauge

from routers.commands import subnet_status

dhcp_leases_total = Counter(
	"dhcp_leases_total",
	"Total de DHCPACK recibidos"
)

dhcp_leases_per_second = Gauge(
	"dhcp_leases_per_second",
	"DHCPACK por segundo"
)

with open("data/config.json", "r") as f:
	data = json.load(f)

ALERT_THRESHOLD = data["dhcp_threshold"]
_last_alert_time = 0
LEASES_THRESHOLD = int(data["subnet_threshold"])

def send_email(subject: None, html: None, text: None):
	msg = MIMEMultipart()
	msg["From"] = data["email"]
	msg["Subject"] = subject
	if text:
		msg.attach(MIMEText(text, "plain"))
	if html:
		msg.attach(MIMEText(html, "html"))
	server = smtplib.SMTP(data["smtp_server"], int(data["smtp_port"]), timeout=10)
	server.starttls()
	server.login(data["email"], data["password"])
	server.sendmail(data["email"], data["emaild"], msg.as_string())
	server.quit()

def send_emailDHCP(pps: int):
	hostname = socket.gethostname()
	subject = f"⚠️ LIMBONET DHCP SERVER {hostname} Alert: {pps} leases/s exceeded threshold"
	timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	ips = []
	for interfaz, direcciones in psutil.net_if_addrs().items():
		for d in direcciones:
			if d.family == socket.AF_INET:
				ip = d.address
				if not ip == "127.0.0.1":
					ips.append((interfaz, ip))
	html = f"""
	<html>
		<body style="font-family:Arial">
			<h1 style="color:red;">DHCP ALERT</h1>
			<p>The DHCP lease rate exceeded the threshold</p>
			<h2>Information:</h2>
			<p><strong>Server:</strong> {hostname}</p>
			<p><strong>Time:</strong> {timestamp}</p><ul>"""
	
	for interfaz, ip in ips:
		html += f"<li>{interfaz}: {ip}</li>"
	
	html += """
			</ul>
		</body>
	</html>
	"""
	text = f"DHCP ALERT: Lease rate {pps} leases/s exceeded threshold of {ALERT_THRESHOLD} leases/s at {timestamp}."
	send_email(subject, html, text)

def send_subnetAlert(subnet: str, usage: float):
	hostname = socket.gethostname()
	subject = f"⚠️ LIMBONET DHCP SERVER {hostname} Subnet Alert: {subnet} at {usage:.1f}% usage."
	timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	html = f"""
	<html>
		<body style="font-family:Arial">
			<h1 style="color:red;">DHCP SUBNET ALERT</h1>
			<p>A DHCP subnet exceeded the configured usage threshold</p>
			<h2>Information:</h2>
			<p><strong>Subnet:</strong> {subnet}</p>
			<p><strong>Usage:</strong> {usage:.1f}%</p>
			<p><strong>Server:</strong> {hostname}</p>
			<p><strong>Time:</strong> {timestamp}</p>
		</body>
	</html>"""
	
	text = f"DHCP ALERT: Subnet {subnet} reached {usage:.1f}% usage at {timestamp}."
	send_email(subject, html, text)

def send_subnetRecovery(subnet: str, usage: float):
	hostname = socket.gethostname()
	subject = f"✅ LIMBONET DHCP SERVER {hostname} Subnet Recovery: {subnet}."
	timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	html = f"""
	<html>
		<body style="font-family:Arial">
			<h1 style="color:red;">DHCP SUBNET RECOVERY</h1>
			<p>The DHCP subnet usage returned to normal levels.</p>
			<h2>Information:</h2>
			<p><strong>Subnet:</strong> {subnet}</p>
			<p><strong>Current Usage:</strong> {usage:.1f}%</p>
			<p><strong>Server:</strong> {hostname}</p>
			<p><strong>Time:</strong> {timestamp}</p>
		</body>
	</html>"""
	
	text = f"DHCP RECOVERY: Subnet {subnet} returned to normall usage levels ({usage:.1f}%) at {timestamp}."
	send_email(subject, html, text)

async def monitor_dhcp():
	global _last_alert_time
	lease_times = deque()
	process = await asyncio.create_subprocess_exec(
		"journalctl",
		"-fu",
		"isc-dhcp-server",
		stdout=asyncio.subprocess.PIPE,
		stderr=asyncio.subprocess.DEVNULL
	)

	try:
		while True:
			line = await process.stdout.readline()
			if not line:
				await asyncio.sleep(0.1)
				continue
			decoded = line.decode(errors="ignore")
			if "DHCPACK" not in decoded:
				continue
			dhcp_leases_total.inc()
			now = time.monotonic()
			lease_times.append(now)
			cutoff = now - 1
			while lease_times and lease_times[0] < cutoff:
				lease_times.popleft()
			pps = len(lease_times)
			dhcp_leases_per_second.set(pps)
			if pps > ALERT_THRESHOLD:
				if now - _last_alert_time > data["dhcp_threshold"]:
					_last_alert_time = now
					await asyncio.to_thread(send_emailDHCP, pps)
	except asyncio.CancelledError:
		process.terminate()
		await process.wait()
		raise

dhcp_alert_state = {}

async def monitor_subnets():
	global dhcp_alert_state
	await asyncio.sleep(5)
	while True:
		try:
			response = subnet_status()
			subnets = response
			for subnet_data in subnets:
				subnet = subnet_data["subnet"]
				total = subnet_data["total"]
				used = subnet_data["used"]
				usage = (used / total) * 100
				if subnet not in dhcp_alert_state:
					dhcp_alert_state[subnet] = False
				if usage >= LEASES_THRESHOLD:
					if not dhcp_alert_state[subnet]:
						send_subnetAlert(subnet, usage)
						dhcp_alert_state[subnet] = True
				else:
					if dhcp_alert_state[subnet]:
						send_subnetRecovery(subnet, usage)
						dhcp_alert_state[subnet] = False
		except Exception as e:
			print ("Monitor_subnets:", e)
		await asyncio.sleep(30)

# Fin del archivo