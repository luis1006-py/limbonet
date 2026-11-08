import subprocess, os, shutil
from datetime import datetime

def obtenerInterfaces():
	interfaces = [line.split(':')[1].split('@')[0].strip()
	for line in subprocess.check_output(['ip', '-o', 'link'], text=True).split('\n') if line]
	return interfaces

def configFichero(interfaces, dhcp4, ip, mask, dg, dns1, dns2):
	texto = ""
	for interfaz in interfaces:
		texto += f"    {interfaz}:\n"
		if dhcp4:
			texto += f"      dhcp4: yes\n"
		else:
			texto += f"      dhcp4: no\n"
			texto += "      addresses:\n"
			texto += f"        - {ip}/{mask}\n"
		if dns1:
			texto += "      nameservers:\n"
			if dns2:
				texto += f"        addresses: [{dns1}, {dns2}]\n"
			else:
				texto += f"        addresses: [{dns1}]\n"
		if dg:
			texto += "      routes:\n"
			texto += "        - to: default\n"
			texto += f"          via: {dg}\n"
	return texto

def configFicheroIN(ruta, interfaces):
	with open(ruta, "a") as f:
		for interfaz in interfaces:
			print ("Configurando interfaz "+interfaz)
			f.write(f"    {interfaz}:\n")
			y = input("¿DHCP? S/N > ")
			if y == "S":
				f.write(f"      dhcp4: yes\n")
			else:
				f.write(f"      dhcp4: no\n")
				ip = input("IP estática (127.0.0.1/24) > ")
				f.write("      addresses:\n")
				f.write(f"        - {ip}\n")
			dg = input("Default Gateway > ")
			if dg:
				f.write("      routes:\n")
				f.write("        - to: default\n")
				f.write(f"          via: {dg}\n")
			dns = input("Servidor DNS > ")
			if dns:
				f.write("      nameservers:\n")
				f.write(f"        addresses: [{dns}]\n")
		f.close()

def aplicarNetplan():
	try:
		netplan_dir = "/etc/netplan/"
		archivos = [f for f in os.listdir(netplan_dir) if f.endswith('.yaml') or f.endswith('.yml')]
		if not archivos:
			print ("No hay archivos YAML, se creará uno...")
			os.system("sudo netplan generate")
			archivos = [f for f in os.listdir(netplan_dir) if f.endswith('.yaml') or f.endswith('.yml')]
		
		if len(archivos) == 1:
			selec = archivos[0]
			print (f"Archivo encontrado: {selec}")
		else:
			print("Archivos encontrados:")
			for i, archivo in enumerate(archivos, 1):
				print(f"{i}. {archivo}")
			while True:
				seleccion = input("Selecciona el número del archivo que quieres editar > ")
				if seleccion.isdigit():
					idx = int(seleccion) - 1
					if 0 <= idx < len(archivos):
						selec = archivos[idx]
						print (f"Has seleccionado {selec}")
						break
					print ("Selección inválida")
		original = os.path.join(netplan_dir, selec)
		formato = datetime.now().strftime("%d%m%Y%H%M")
		backup = os.path.join(netplan_dir, selec + formato + ".backup")
		output = './output/file.yaml'
		os.rename(original, backup)
		print (f"Creado backup de {original} como {backup}")
		shutil.move(output, original)
		print ("Operación completada, aplicando cambios...")
		subprocess.run(['sudo', 'netplan', 'apply'])
		print ("Configuración aplicada correctamente")
	except Exception as e:
		print (f"Error: {e}")