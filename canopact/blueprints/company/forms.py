from flask_wtf import Form
from wtforms.validators import DataRequired
from wtforms_components import EmailField, Email


class InviteForm(Form):
    email = EmailField('User Email', validators=[DataRequired(), Email()])
