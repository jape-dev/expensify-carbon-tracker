from lib.util_wtforms import ModelForm
from wtforms.validators import DataRequired
from wtforms_components import EmailField, Email


class WaitingListForm(ModelForm):
    email = EmailField('',
                       validators=[
                        DataRequired(),
                        Email()])
