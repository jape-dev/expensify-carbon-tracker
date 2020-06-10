"""Views for Canopact carbon dashboard.

Example:


"""
from flask import Blueprint, render_template


carbon = Blueprint('carbon', __name__, template_folder='templates')


@carbon.route('/carbon', methods=['GET', 'POST'])
def carbon_dashboard():
    """Renders template for the carbon dashboard"""
    return render_template('carbon_dashboard.html',
                           report_id=5)
