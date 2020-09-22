from canopact.extensions import mail
from canopact.blueprints.contact.tasks import deliver_contact_email


class TestTasks(object):
    def test_deliver_support_email(self):
        """ Deliver a contact email.

        Notes:
          Changed test email to have an @canopact domain due to
          zoho mail bug: https://canopact.atlassian.net/browse/CPT-39.
        """
        form = {
          'email': 'james@canopact.com',
          'message': 'Test message from Snake Eyes.'
        }

        with mail.record_messages() as outbox:
            deliver_contact_email(form.get('email'), form.get('message'))

            assert len(outbox) == 1
            assert form.get('email') in outbox[0].body
