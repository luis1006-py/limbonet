from .auth import auth_bp
from .forms import forms_bp
from .panel import panel_bp
from .dhcp_bp import dhcp_bp
from .dns_bp import dns_bp
from .netplan_bp import netplan_bp
from .local import local_bp

blueprints = [auth_bp, forms_bp, panel_bp, dhcp_bp, dns_bp, netplan_bp]
blueprints_local = blueprints + [local_bp]