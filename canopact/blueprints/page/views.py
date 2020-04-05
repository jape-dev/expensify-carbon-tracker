"""Flask blueprint for rendering landing page."""

from flask import Blueprint
from flask import render_template


page = Blueprint('page', __name__, template_folder='templates')


@page.route('/')
def home():
    # return 'Hello World, this is Canopact'
    return render_template('page/home.html')
