from flask_wtf import Form
from wtforms import HiddenField, StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp
from wtforms_components import EmailField, Email, Unique

from config.settings import LANGUAGES, INDUSTRIES, EMPLOYEES
from lib.util_wtforms import ModelForm, choices_from_dict
from canopact.blueprints.user.models import User, db
from canopact.blueprints.user.validations import ensure_identity_exists, \
    ensure_existing_password_matches
import pycountry


class LoginForm(Form):
    next = HiddenField()
    identity = StringField('Username or email',
                           [DataRequired(), Length(3, 254)])
    password = PasswordField('Password', [DataRequired(), Length(8, 128)])
    # remember = BooleanField('Stay signed in')


class BeginPasswordResetForm(Form):
    identity = StringField('Username or email',
                           [DataRequired(),
                            Length(3, 254),
                            ensure_identity_exists])


class PasswordResetForm(Form):
    reset_token = HiddenField()
    password = PasswordField('Password', [DataRequired(), Length(8, 128)])


class SignupForm(ModelForm):
    email = EmailField('Company Email',
                       validators=[
                        DataRequired(),
                        Email(),
                        Unique(
                            User.email,
                            get_session=lambda: db.session
                        )
                        ])
    name = StringField('Company Name', [DataRequired()])
    employees = SelectField('Employees',
                            choices=choices_from_dict(EMPLOYEES,
                                                      prepend_blank=False))
    industry = SelectField('Industry',
                           choices=choices_from_dict(INDUSTRIES,
                                                     prepend_blank=False),
                           default='Please Select')
    country = SelectField('Country of Company',
                          choices=[(
                              country.alpha_2,
                              country.name) for country in pycountry.countries
                              ],
                          default='GB')
    job_title = StringField('Job Title')
    password = PasswordField('Password', [DataRequired(), Length(8, 128)])
    invited = False


class ResendEmailForm(Form):
    identity = StringField("Didn't recieve an email? Re-enter below:",
                           [DataRequired(),
                            Length(3, 254),
                            ensure_identity_exists])


class WelcomeForm(ModelForm):
    username_message = 'Letters, numbers and underscores only please.'

    username = StringField(validators=[
        Unique(
            User.username,
            get_session=lambda: db.session
        ),
        DataRequired(),
        Length(1, 16),
        # Part of the Python 3.7.x update included updating flake8 which means
        # we need to explicitly define our regex pattern with r'xxx'.
        Regexp(r'^\w+$', message=username_message)
    ])


class UpdateCredentialsForm(ModelForm):
    current_password = PasswordField('Current password',
                                     [DataRequired(),
                                      Length(8, 128),
                                      ensure_existing_password_matches])

    email = EmailField(validators=[
        Email(),
        Unique(
            User.email,
            get_session=lambda: db.session
        )
    ])
    password = PasswordField('Password', [Optional(), Length(8, 128)])


class ExpensifyAPICredentialsForm(ModelForm):
    partnerUserID = StringField('partnerUserID',
                                [DataRequired(),
                                 Length(3, 254)])

    partnerUserSecret = StringField('partnerUserSecret',
                                    [DataRequired(),
                                     Length(3, 254)])


class UpdateLocaleForm(Form):
    locale = SelectField('Language preference', [DataRequired()],
                         choices=choices_from_dict(LANGUAGES,
                                                   prepend_blank=False))
