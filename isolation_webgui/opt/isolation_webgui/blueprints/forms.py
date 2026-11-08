from flask import Blueprint
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

forms_bp = Blueprint("forms", __name__)

class LoginForm(FlaskForm):
	usuario = StringField("Usuario", validators=[
		DataRequired(message="Es obligatorio el nombre de usuario"),
		Length(min=3, max=20, message="El usuario debe tener entre 3 y 20 caracteres")
	],
	render_kw={"autocomplete": "username"}
	)

	contraseña = PasswordField("Contraseña", validators=[
		DataRequired(message="La contraseña es obligatoria"),
		Length(min=3, max=100, message="La contraseña debe tener al menos 8 caracteres")
	],
	render_kw={"autocomplete": "current-password"}
	)

	submit = SubmitField("Entrar", render_kw={"data-i18n-value": "access"})