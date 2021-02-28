from flask_wtf import Form
from wtforms import (
  StringField,
  FormField,
  FieldList
)
from wtforms.validators import (
  Length,
  Optional
)
from wtforms.widgets.html5 import DateInput


class SearchForm(Form):
    q = StringField('Search terms', [Optional(), Length(1, 256)])


class RouteForm(Form):
    origin = StringField([Optional(),  Length(1, 256)])
    destination = StringField([Optional(),  Length(1, 256)])


class JourneysForm(Form):
    ids = []
    journeys = FieldList(FormField(RouteForm))


class DateForm(Form):
    date = StringField(widget=DateInput())
