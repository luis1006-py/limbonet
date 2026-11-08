import subprocess, shutil
from datetime import datetime
# Necesita tener isc-dhcp-server instalado

def formatDHCP(user):
	with open ("config/dhcp.txt", "r") as f:
		data = f.read()
	with open("./output/"+user+"/"+"dhcpd.conf", 'w') as f:
		f.write(data+"\n")
	

def aplicarDHCP():
	dhcp_dir = "/etc/dhcp/"
	file = "dhcpd.conf"
	try:
		formato = datetime.now().strftime("%d%m%Y%H%M")
		shutil.copy2(dhcp_dir + file, dhcp_dir + file + formato + ".backup")
		print ("Copia de seguridad creada en " + dhcp_dir + file + formato + ".backup")
		original = dhcp_dir + file
		output = './output/dhcpd.conf'
		shutil.move(output, original)
		print ("Archivo movido a " + original)
	except Exception as e:
		print (f"Error al mover el archivo: {e}")
		return

	print ("Reiniciando el servicio de DHCP...")
	subprocess.run(["sudo", "service", "isc-dhcp-server", "restart"], check=True)
	print ("Servicio reiniciado, verifica su estado con 'sudo service isc-dhcp-server status'.")

def subnetIN():
	red = input("Red (127.0.0.0) > ")
	mascara = input("Máscara (255.255.255.0) > ")
	rango1 = input("Rango inicio > ")
	rango2 = input("Rango fin > ")
	dns1 = input("DNS primario > ")
	dns2 = input("DNS secundario (opcional) > ")
	dnsname = input("Nombre de dominio (opcional) > ")
	subnetmask = input("Máscara de subred (opcional) > ")
	dg = input("Default Gateway (opcional) > ")
	broadcast = input("Dirección de broadcast (opcional) > ")
	lease = input("Tiempo de lease por defecto en segundos (opcional) > ")
	maxlease = input("Tiempo máximo de lease en segundos (opcional) > ")
	with open("output/dhcpd.conf", "a") as f:
		f.write(subnet(red, mascara, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease)+'}\n')

def subnet(red, mascara, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease):
	text = f"subnet {red} netmask {mascara} {"{"}\n"
	if rango1 and rango2:
		text+= f"  range {rango1} {rango2};\n"
	if dns2:
		text+= f"  option domain-name-servers {dns1}, {dns2};\n"
	elif dns1:
		text+= f"  option domain-name-servers {dns1};\n"
	if dnsname:
		text+= f'  option domain-name "{dnsname}";\n'
	if subnetmask:
		text+= f"  option subnet-mask {subnetmask};\n"
	if dg:
		text+= f"  option routers {dg};\n"
	if broadcast:
		text+= f"  option broadcast-address {broadcast};\n"
	if lease:
		text+= f"  default-lease-time {lease};\n"
	if maxlease:
		text+= f"  max-lease-time {maxlease};\n"
	return text

def reservaIN():
	name = input("Nombre del host > ")
	mac = input("Dirección MAC > ")
	ip = input("IP fija a asignar > ")
	dns1 = input("DNS primario > ")
	dns2 = input("DNS secundario (opcional) > ")
	dg = input("Default Gateway (opcional) > ")
	with open("output/dhcpd.conf", "a") as f:
		f.write(reserva(name, mac, ip, dns1, dns2, dg))

def reserva(name, mac, ip, dns1, dns2, dg):
	text = f"host {name} {"{"}\n"
	text+= f"  hardware ethernet {mac};\n"
	text+= f"  fixed-address {ip};\n"
	if dns2:
		text+= f"  option domain-name-servers {dns1}, {dns2};\n"
	elif dns1:
		text+= f"  option domain-name-servers {dns1};\n"
	if dg:
		text+= f"  option routers {dg};\n"
	text+='}\n'
	return text

def claseIN():
	print ("Puedes usar MSFT para Windows")
	print ("Esto debe estar ARRIBA de la configuración de la subred")
	while True:
		print ("*****************")
		print ("1.- Regla por ID")
		print ("2.- Regla por MAC")
		print ("*****************")
		print ("Regla de clase (q para salir) > ")
		x = input (" > ")
		if x == "q":
			print ("Saliendo...")
			break
		else:
			nameclass = input("Nombre de clase > ")
			if x == "1":
				id = input ("ID > ")
				with open("output/dhcpd.conf", "a") as f:
					f.write(claseID(nameclass, id))
			elif x == "2":
				mac = input("Mac (00:00:00) > ")
				print ("1.- La MAC debe empezar por "+mac)
				print ("2.- La MAC debe terminar por "+mac)
				y = input (" > ")
				with open("output/dhcpd.conf", "a") as f:
					f.write(claseMAC(nameclass, mac, y))
			else:
				print ("Elección inválida, volviendo...")

def macBinary(mac):
	bytes = mac.split(':')
	binary = ''.join(f'\\x{b.upper()}' for b in bytes)
	return binary

def claseMAC(nombre, mac, regla):
	mac = macBinary(mac)
	text = f'class "{nombre}"'+' {\n'
	if regla == "1": # inicio
		text += f'  match if substring(hardware, 1, 3) = {mac};\n'
	elif regla == "2": # final
		text += f'  match if substring(hardware, 4, 3) = {mac};\n'
	text += '}\n'
	return text

def claseID(nombre, id):
	text = f'class "{nombre}"'+' {\n'
	text+= f'  match if substring (option vendor-class-identifier, 0, 4) = "{id}";\n'
	text += '}\n'
	return text

def poolIN():
	print ("Debe de ser la misma configuración que en Subnet")
	red = input("Red (127.0.0.0) > ")
	mascara = input("Máscara (255.255.255.0) > ")
	rango1 = input("Rango inicio > ")
	rango2 = input("Rango fin > ")
	dns1 = input("DNS primario > ")
	dns2 = input("DNS secundario (opcional) > ")
	dnsname = input("Nombre de dominio (opcional) > ")
	subnetmask = input("Máscara de subred (opcional) > ")
	dg = input("Default Gateway (opcional) > ")
	broadcast = input("Dirección de broadcast (opcional) > ")
	lease = input("Tiempo de lease por defecto en segundos (opcional) > ")
	maxlease = input("Tiempo máximo de lease en segundos (opcional) > ")
	# La información se va a guardar SIN el "}" de cierre
	with open("output/dhcpd.conf", "a") as f:
		f.write(subnet(red, mascara, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease))
	
	while True:
		print ("Introduce el nombre de la clase a configurar (q para salir)")
		x = input (" > ")
		if x == "q":
			break
		else:
			y = input ("¿Permitir (allow) o denegar (deny)? > ")
			rango1 = input("Rango inicio > ")
			rango2 = input("Rango fin > ")
			dns1 = input("DNS primario > ")
			dns2 = input("DNS secundario (opcional) > ")
			dnsname = input("Nombre de dominio (opcional) > ")
			subnetmask = input("Máscara de subred (opcional) > ")
			dg = input("Default Gateway (opcional) > ")
			broadcast = input("Dirección de broadcast (opcional) > ")
			lease = input("Tiempo de lease por defecto en segundos (opcional) > ")
			maxlease = input("Tiempo máximo de lease en segundos (opcional) > ")
		# La información se va a guardar SIN el "}" de cierre (quitado de la función para agregarlo aquí)
		with open("output/dhcpd.conf", "a") as f:
			f.write(pool(y, x, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease))
	with open("output/dhcpd.conf", "a") as f:
		f.write("}\n")
	print ("Configuración agregada a output/dhcpd.conf")

def pool(permiso, clase, rango1, rango2, dns1, dns2, dnsname, subnetmask, dg, broadcast, lease, maxlease):
	text = "  pool {\n"
	text+=f'    {permiso} members of "{clase}";\n'
	if rango1 and rango2:
		text+= f"    range {rango1} {rango2};\n"
	if dns2:
		text+= f"    option domain-name-servers {dns1}, {dns2};\n"
	elif dns1:
		text+= f"    option domain-name-servers {dns1};\n"
	if dnsname:
		text+= f'    option domain-name "{dnsname}";\n'
	if subnetmask:
		text+= f"    option subnet-mask {subnetmask};\n"
	if dg:
		text+= f"    option routers {dg};\n"
	if broadcast:
		text+= f"    option broadcast-address {broadcast};\n"
	if lease:
		text+= f"    default-lease-time {lease};\n"
	if maxlease:
		text+= f"    max-lease-time {maxlease};\n"
	text += "  }\n"
	return text
