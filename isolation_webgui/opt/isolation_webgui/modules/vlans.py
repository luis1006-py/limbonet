import shutil, subprocess, os
from modules.colores import Fore

def comando_disponible(comando):
	return shutil.which(comando) is not None

def configPerma():
	# Nota esto se va a hacer con Netplan
	# Ejecutar esto: sudo apt install vlan
	# Ejecutar esto: sudo modprobe 8021q
	print ("Configuración de VLAN permanente con Netplan")
	subprocess.run(["sudo", "modprobe", "8021q"], check=True)
	interfaces = []
	for iface in os.listdir('/sys/class/net/'):
		interfaces.append(iface)
	interfaces.remove("lo")
	print ("Interfaces disponibles:")
	for i, iface in enumerate(interfaces, 1):
		print (f"{i}. {iface}")
	while True:
		seleccion = input("Selecciona la interfaz a usar > ")
		if seleccion.isdigit():
			idx = int(seleccion) - 1
			if 0 <= idx < len(interfaces):
				iface = interfaces[idx]
				print (f"Has seleccionado {iface}")
				break
			print ("Selección inválida")
	vlan_id = input("Introduce el ID de la VLAN (1-4094) > ")
	if vlan_id.isdigit() and 1 <= int(vlan_id) <= 4094:
		#vlan_iface = f"{iface}.{vlan_id}"
		ip = input("Introduce la IP a asignar (formato CIDR) > ")
		dg = input("Introduce la dirección del Default Gateway > ")
		print ("Usando el DNS de Google (8.8.8.8)")
		file = open('output/file.yaml', 'a')
		file.write(f"  vlans:\n")
		file.write(f"    vlan{str(id)}:\n")
		file.write(f"      id: {vlan_id}\n")
		file.write(f"      link: {iface}\n")
		file.write(f"      addresses: [{ip}]\n")
		file.write(f"      gateway4: {dg}\n")
		file.write(f"      nameservers:\n")
		file.write(f"        addresses: [8.8.8.8]\n")
		file.close()
		print (f"VLAN {vlan_id} configurada correctamente")
		print ("La configuración se ha añadido a output/file.yaml, debe ser agregada a la configuración de Netplan")
		print ("Después ejecuta netplan apply para aplicar los cambios")
	else:
		print (Fore.ROJO + "ID de VLAN inválido." + Fore.RESET)


def configNotPerma(interfaces):
	# comandos disponibles: vconfig, ifconfig, dhclient, ip
	print ("Buscando interfaces de red...")
	interfaces.remove("lo")
	print ("Interfaces disponibles:")
	for i, iface in enumerate(interfaces, 1):
		print (f"{i}. {iface}")
	while True:
		seleccion = input("Selecciona la interfaz a usar > ")
		if seleccion.isdigit():
			idx = int(seleccion) - 1
			if 0 <= idx < len(interfaces):
				iface = interfaces[idx]
				print (f"Has seleccionado {iface}")
				break
			print ("Selección inválida")
	vlan_id = input("Introduce el ID de la VLAN (1-4094) > ")
	if vlan_id.isdigit() and 1 <= int(vlan_id) <= 4094:
		vlan_iface = f"{iface}.{vlan_id}"
		try:
			print (f"Creando VLAN {vlan_id} en {iface}...")
			subprocess.run(["sudo", "vconfig", "add", iface, vlan_id], check=True)
			subprocess.run(["sudo", "ifconfig", vlan_iface, "up"], check=True)
			x = input("¿Quieres obtener una IP vía DHCP? (S/N) > ")
			if x == "S":

				print (f"VLAN {vlan_id} creada como {vlan_iface}. Obteniendo IP vía DHCP...")
				subprocess.run(["sudo", "dhclient", vlan_iface], check=True)
			else:
				ip = input("Introduce la IP a asignar (formato CIDR) > ")
				subprocess.run(["sudo", "ifconfig", vlan_iface, ip, "up"], check=True)

			print (f"VLAN {vlan_iface} configurada correctamente.")
			print ("Usa 'ifconfig' para ver la configuración.")
		except subprocess.CalledProcessError as e:
			print (Fore.ROJO + f"Error al crear la VLAN: {e}" + Fore.RESET)
	else:
		print (Fore.ROJO + "ID de VLAN inválido." + Fore.RESET)