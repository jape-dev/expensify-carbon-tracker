"""Module for interacting with the Salesforce web server API.

Original Author: "Jean-Claude Tissier"
https://github.com/jctissier/Salesforce-Oauth2-REST-Metadata-
API-Python-Examples"

"""

import requests
from urllib.parse import quote
import urllib.parse as urlparse
import webbrowser


class SalesforceOAuth2():
    """Salesforce Web Server Oauth Authentication Flow"""

    _authorization_url = '/services/oauth2/authorize'
    _token_url = '/services/oauth2/token'

    def __init__(self, client_id, client_secret, redirect_uri, sandbox=False):
        """
        Create SalesforceOauth2 object
        :param client_id: Connected App's Consumer Key
        :param client_secret: Connected App's Consumer Secret
        :param redirect_uri: Callback URL once logged in
        :param sandbox: Boolean flag to determine authentication site
        """
        if sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'
        self.redirect_uri = redirect_uri
        self._client_id = client_id
        self._client_secret = client_secret

    def authorize_login_url(self):
        """
        URL to login through Salesforce
        :return: Redirect URL for Oauth2 authentication
        """

        return "{site}{authorize_url}" \
               "?response_type=code&client_id={client_id}" \
               "&redirect_uri={redirect_uri}&prompt=login".format(
                    site=self.auth_site,
                    authorize_url=self._authorization_url,
                    client_id=self._client_id,
                    redirect_uri=quote(self.redirect_uri)
                )

    def get_access_token(self, code):
        """
        Sets the body of the POST request
        :return: POST response
        """
        body = {
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code,
            'client_id': self._client_id,
            'client_secret': self._client_secret
        }
        response = self._request_token(body)

        return response

    def get_access_token_refresh(self, refresh_token):
        """
        Sets the body of the POST request
        :return: POST response
        """
        body = {
            'grant_type': 'refresh_token',
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': refresh_token
        }
        response = self._request_token(body)

        return response

    def _request_token(self, data):
        """
        Sends a POST request to Salesforce to authenticate credentials
        :param data: body of the POST request
        :return: POST response
        """
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(
            "{site}{token_url}".format(
                site=self.auth_site,
                token_url=self._token_url
            ),
            data=data,
            headers=headers
        )

        return response


def get_config():
    """Gwetter function for SF config to prevent circular imports"""
    from canopact.app import create_app
    app = create_app()

    id = app.config['SF_CLIENT_ID']
    secret = app.config['SF_CLIENT_SECRET']
    uri = app.config['SF_REDIRECT_URI']

    return id, secret, uri


def get_redirect_url():
    """Get the redirect url for the user to authenticate their account.

    Returns:
        oauth_redirect (str): redirct url.

    """
    client_id, client_secret, redirect_uri = get_config()

    oauth = SalesforceOAuth2(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )

    oauth_redirect = oauth.authorize_login_url()

    return oauth_redirect


def get_tokens(code):
    """Get the access and refresh token for the Oauth flow.

    Args:
        code (str): code required for the authentication url.

    Returns:
        access_token (str): access_token.
        refresh_token (str): refresh_token.

    """
    client_id, client_secret, redirect_uri = get_config()

    oauth = SalesforceOAuth2(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
    # Retrieve access_token from Salesforce by sending authenticated code
    sf_authentication = oauth.get_access_token(code)
    access_token = sf_authentication.json().get("access_token")
    refresh_token = sf_authentication.json().get("refresh_token")

    return access_token, refresh_token


def main():
    """E2E Outh2 flow to authenticate salesforce account.

    Returns:
        json: relevant tokens and meta data from authentication.

    """
    client_id, client_secret, redirect_uri = get_config()

    oauth = SalesforceOAuth2(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )

    oauth_redirect = oauth.authorize_login_url()
    webbrowser.open(oauth_redirect)

    callback_url = input('Copy-Paste your callback URL and press ENTER: ')
    # Extract the code from the URL.
    extract_code = urlparse.urlparse(callback_url)
    code = urlparse.parse_qs(extract_code.query)['code'][0]

    # Retrieve access_token from Salesforce by sending authenticated code.
    sf_authentication = oauth.get_access_token(code)
    refresh_token = sf_authentication.json().get("refresh_token")
    sf_authentication_refresh = oauth.get_access_token_refresh(refresh_token)

    return sf_authentication_refresh.json()


if __name__ == "__main__":
    main()
