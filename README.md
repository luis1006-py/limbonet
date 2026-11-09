# LIMBONET ⚠️ OBSOLETO

Este proyecto ha quedado obsoleto y ya no se mantiene. Su contenido puede estar desactualizado y no se realizarán nuevas actualizaciones ni correcciones.

---

**Limbonet** es una plataforma cliente-servidor de código abierto diseñada para la gestión centralizada, visual y segura de servicios de red (**DNS y DHCP**) en nodos Linux. Está orientada principalmente a PYMES con recursos técnicos limitados, entornos educativos y laboratorios que buscan simplificar la administración de redes sin depender de configuraciones manuales propensas a errores o de las limitaciones de los routers domésticos.

## Arquitectura del Sistema

El sistema se divide en dos componentes principales desacoplados para mayor seguridad y escalabilidad:

1. **Limbonet WebGUI:** Aplicación central desarrollada en **Flask** que ofrece una interfaz web, gestiona usuarios (Bcrypt y protección CSRF), valida parámetros y genera los ficheros de configuración.
2. **Limbonet Service:** Servicio  basado en **FastAPI** ejecutado en los nodos gestionados. Recibe los ficheros de configuración de forma remota, valida la autenticidad mediante **API Key**, comprueba la sintaxis de los servicios locales y aplica los cambios.

## Características Principales

* **Administración Centralizada:** Gestiona múltiples servidores y nodos Linux desde un único panel web.
* **Interfaz Multidioma:** Disponible en **Español, Euskara, Inglés, Francés, Ucraniano, Turco, Japonés y Chino (Simplificado y Tradicional)**.
* **Gestión DHCP:** Configuración visual de ámbitos (subnets), reservas por dirección MAC, clases de dispositivos, pools de direcciones y monitorización de concesiones (leases) con estadísticas de fabricantes.
* **Gestión DNS:** Creación y mantenimiento de zonas directas, zonas inversas (`in-addr.arpa`) y ficheros de base de datos (`.db`).
* **Validación de Seguridad:** Comprobación automática de errores antes de aplicar cambios mediante herramientas nativas (`named-checkconf`, `named-checkzone`, `dhcpd -t`).
* **Seguridad y Auditoría:** Autenticación por contraseña hasheada (Bcrypt), consultas SQL parametrizadas, control de acceso por API Key, cifrado HTTPS y registro detallado de eventos (logs).
* **Monitorización y Alertas Automáticas:** Envío de notificaciones vía SMTP configuradas mediante umbrales ante situaciones críticas:
  * Cuando una subred DHCP se encuentra próxima al agotar su capacidad de IPs disponibles.
  * Cuando el número de concesiones por segundo supera el umbral establecido.
---

## Guía de Uso Rápido

### 1. Acceso a la WebGUI
* **URL por defecto:** `https://127.0.0.1:5000`
* **Credenciales iniciales:** `admin` / `admin` *(Se recomienda modificarlas tras el primer inicio de sesión).*

### 2. Vincular un Nodo
1. Instale y ejecute `Limbonet-service` en el nodo de destino.
2. Obtenga la **API Key** del nodo.
3. En la interfaz web de la WebGUI, navegue al panel de dispositivos y seleccione **"Vincular dispositivo"**.
4. Introduzca la dirección IP del nodo y la API Key correspondiente para establecer la relación de confianza.

---

## Tecnologías Utilizadas

* **Backend:** Python, Flask, Jinja2, Requests, Bcrypt.
* **Agente:** Python, FastAPI.
* **Bases de Datos:** SQLite.
* **Frontend:** HTML, JavaScript, CSS.
