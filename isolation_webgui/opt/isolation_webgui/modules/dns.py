import shutil

def zonainversaIN():
	red = input("Introduce la dirección de la red excluyendo el final (192.168.1) > ")
	red = red.strip().rstrip('.')
	octs = red.split('.')
	if len(octs) in (3, 4) and all(o.isdigit() and 0 <= int(o) <= 255 for o in octs):
		reversed_ip = '.'.join(octs[::-1])
		print(f"Dirección: {reversed_ip}.in-addr.arpa")
	else:
		print("Formato inválido.")
		return
	db = input("Introduce el nombre de la DB > ")
	with open("output/named.conf.local", "a") as f:
		f.write(zonaInversa(reversed_ip, db))

def zonaDirectaIN():
	name = input("Introduce el nombre de la zona directa > ")
	db = input("Introduce el nombre de la DB > ")
	with open("output/named.conf.local", "a") as f:
		f.write(zonaDirecta(name, db))

def zonaInversa(reversed_ip, db):
	text = 'zone "'+reversed_ip+'.in-addr.arpa" {\n'
	text += "	type master;\n"
	text += f'	file "/etc/bind/{db}"\n'
	text += "};\n\n"
	return text

def zonaDirecta(name, db):
	text = 'zone "'+name+'" {\n'
	text += "	type master;\n"
	text += f'	file "/etc/bind/{db}"\n'
	text += "};\n\n"
	return text

def configBDIN(bdname):
	print("Advertencia si usas el FQDN (nombre completo) agrega un punto final")
	print("Si escribes example.com se referirá a example.com.example.com")
	print("Si escribes www. se referirá al dominio www (no existe)")
	MNAME = input("Nombre maestro > ") or "localhost."
	contact = input("Contacto > ") or "root.localhost."
	
	TTL = input("Default TTL (opcional) > ") or "86400"
	serial = input("Serial (opcional) > ") or "1"
	refresh = input("Refresh (opcional) > ") or "604800"
	retry = input("Retry (opcional) > ") or "86400"
	expire = input("Expire (opcional) > ") or "2419200"
	negativeCacheTTL = input("Negative Cache TTL (opcional) > ") or "86400"

	nameserver = input("Nameserver autoritativo > ") or "localhost."
	dirIP = input("Dirección IP de la zona (opcional) > ") or None

	with open(f"output/{bdname}", "w") as f:
		f.write(configBD(MNAME, contact, TTL, serial, refresh, retry, expire, negativeCacheTTL, nameserver, dirIP))

def configBD(MNAME, contact, TTL, serial, refresh, retry, expire, negativeCacheTTL, nameserver, dirIP):
	text = f"$TTL {TTL}\n"
	text+= f"@	IN	SOA	{MNAME} {contact} (\n"
	text+= f"			{serial}		; Serial\n"
	text+= f"			{refresh}		; Refresh\n"
	text+= f"			{retry}		; Retry\n"
	text+= f"			{expire}		; Expire\n"
	text+= f"			{negativeCacheTTL} )		; Negative Cache TTL\n"
	text+= ";\n"

	text+= f"@	IN	NS	{nameserver}\n"
	if dirIP:
		text+= f"@	IN	A	{dirIP}\n"
	return text

def addRegister(dato, register, value):
	text = f"{dato}	IN	{register}	{value}\n"
	return text

def addRegisterIN(bdname):
	print ("Si es zona directa, introduce el host o FQDN con punto final")
	print ("Si es zona inversa, introduce el último octeto de la IP")
	print ("Para referirte a la zona actual, usa @")
	dato = input("Dato a añadir en el registro > ")
	print ("A para zonas directas y PTR para zonas inversas")
	register = input("Tipo de registro > ")
	value = input("Valor del registro > ")
	with open(f"output/{bdname}", "a") as f:
		f.write(addRegister(dato, register, value))

def crearBD(name):
	shutil.copy("config/db.empty", f"output/{name}")

# Agregarlo a ISOLATION old

def vaciarDNS():
	with open("./output/named.conf.local", 'w') as f:
		pass