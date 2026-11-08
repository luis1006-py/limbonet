import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

def load_public(path):
	with open(path, "rb") as key_file:
		key = serialization.load_pem_public_key(key_file.read())
		if isinstance(key, rsa.RSAPublicKey):
			return key
		else:
			raise ValueError("La clave pública no es una clave RSA válida.")
	
def load_private(path):
	with open(path, "rb") as key_file:
		return serialization.load_pem_private_key(key_file.read(), password=None)

# Verificación de la firma con RSA
def verify_signature(public_key, message, signature):
	if isinstance(public_key, rsa.RSAPublicKey):
		public_key.verify(
			signature,
			message,
			padding.PKCS1v15(),
			hashes.SHA256()
		)
	else:
		raise TypeError("La clave proporcionada no es una clave RSA.")

def rsa_encrypt(public_key, data: bytes) -> str:
	out = public_key.encrypt(
		data, 
		padding.OAEP(
			mgf=padding.MGF1(algorithm=hashes.SHA256()),
			algorithm=hashes.SHA256(),
			label=None
		)
	)
	return base64.b64encode(out).decode()

def rsa_decrypt(private_key, data_b64: str) -> bytes:
	raw = base64.b64decode(data_b64)
	return private_key.decrypt(
		raw,
		padding.OAEP(
			mgf=padding.MGF1(hashes.SHA256()),
			algorithm=hashes.SHA256(),
			label=None
		)
	)