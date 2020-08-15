"""Classes and methods for making requests to the Expensify Public API.

Examples:
    userid = "integration_username"
    secret = "integration_password"
    template = my_template
    ex = Expensify(userid, secret, template)
    reports = ex.reports()
"""

import ast
import json
import requests
import time

from vendors import freemarker_templates


class Expensify():
    """Methods for fetching data from the Expensify public API.

    Args:
        user_id (str): expensify api user id.
        secret (str): expensify api secret token.
        template (str): FreeMarker template for formatting request response.

    Attributes:
        url (str): url for integration server for making api requests.
    """

    def __init__(self, userid, secret, template):
        self.userid = userid
        self.secret = secret
        self.template = template
        self.url = ("https://integrations.expensify.com/Integration-Server/"
                    "ExpensifyIntegrations")

    def reports(self, start_timestamp=None):
        """Wrapper function for requesting and fetching report file.

        Args:
            start_timestamp (datetime): date to fetch reports from.
        """
        if start_timestamp is None:
            # Default to a month ago.
            start_timestamp = time.time() - (24 * 3600 * 30)

        report_filename = self.generate_report(start_timestamp)
        report = self.fetch_file(report_filename)
        return report

    def generate_report(self, start_timestamp):
        """Creates parameter JSON for requesting report and generates filename.

        Requests all reports where the report was created or updated
        after `start_timestamp`.

        Args:
            start_timestamp (datetime): date to fetch reports from.

        Returns:
            str: filename to fetch from the Expensify API.
        """

        params = {
            "requestJobDescription": json.dumps({
                "type": "file",
                "credentials": {
                    "partnerUserID": self.userid,
                    "partnerUserSecret": self.secret
                },
                "onReceive": {
                    "immediateResponse": ["returnRandomFileName"]
                },
                "inputSettings": {
                    "type": "combinedReportData",
                    "filters": {
                        "startDate": time.strftime("%Y-%m-%d",
                                                   time.gmtime(start_timestamp)
                                                   )
                    }
                },
                "outputSettings": {
                    "fileExtension": "json",
                    "fileBasename": "expense_report"
                }
                }),
            "template": self.template
        }
        requests.session().close()
        response = requests.get(self.url, params=params)
        requests.session().close()
        response_content = response.content
        return_response = response_content.decode('ascii')

        if response.content.endswith(b".json"):
            return return_response
        else:
            raise RuntimeError(f"Failed to generate Expensify report, "
                               f"their API responded with {response.content}")

    def fetch_file(self, filename):
        """Given a `filename`, fetch it from Expensify.

        Args:
            filename (str): filename to fetch from Expensify.

        Returns:
            return_response (JSON): object containing Expensify reports.
        """
        params = {
            "requestJobDescription": json.dumps({
                "type": "download",
                "credentials": {
                    "partnerUserID": self.userid,
                    "partnerUserSecret": self.secret,
                },
                "fileName": str(filename)
                })
            }

        response = requests.get(self.url, params=params)
        requests.session().close()
        response_content = response.content
        return_response = response_content.decode('utf-8')
        return_response = ast.literal_eval(return_response)

        if response.status_code == 200:
            return return_response
        else:
            raise RuntimeError("Failed to fetch a file from Expensify, "
                               "their API responded with: "
                               "%s" % response.content)

    @classmethod
    def convert_missing_to_null(cls, reports, expenses_col="report_expenses"):
        """Converts all missing values in the Expensify report to None types.

        Args:
            reports (list): list of report dictionaries.
            expenses_col (str): key name in `reports` for the expenses values.

        Calls:
            Expensify.count_expenses()

        Returns:
            list: cleaned report dictionaries with None instead of ''.
        """
        cleaned_reports = []
        missing = ['']
        empty = []
        null = [None]

        for r in reports:
            # Get the number of expenses in each report.
            exp_count = Expensify.count_expenses(r)
            # Expand `missing` and `null` to match the number of expenses.
            missing_values = missing * exp_count
            empty_values = empty * exp_count
            null_values = null * exp_count

            # Get the dict that contains expenses.
            exp = r[expenses_col]
            # Replace `missing_values` with `null_values`.
            exp_cleaned = {k: null_values if (v == missing_values or
                           v == empty_values) else v for k, v in exp.items()}
            # Update the value for the `expenses_col` key.
            r[expenses_col] = exp_cleaned
            # Add cleaned report dict to the json list.
            cleaned_reports.append(r)

        return cleaned_reports

    @classmethod
    def count_expenses(cls, report, expenses_col="report_expenses",
                       count_col="expense_id"):
        """Counts the number of expenses in an Expensify report.

        Args:
            report (JSON): Expensify report.
            expenses_col (str): key name in `reports` for the expenses values.
            count_col (str): name of key used to count reports.

        Returns:
            int: number of expenses in the report.
        """
        data = report[expenses_col]
        num_expenses = len(data[count_col])

        return num_expenses

    @staticmethod
    def convert_data_types(reports, expenses_col="report_expenses",
                           float_cols=["expense_amount",
                                       "expense_converted_amount",
                                       "expense_modified_amount",
                                       "expense_unit_rate"],
                           int_cols=["expense_id",
                                     "expense_unit_count"]):
        """Converts values to the required datatype

        Args:
            reports (list): list of report dictionaries.
            expenses_col (str): key name in `reports` for the expenses values.
            float_cols (list): keys to have values converted into floats.
            int_cols (list): keys to have values converted into integers.

        Returns:
            list: reports with values converted into the requires types.

        TODO:
            Filter out the NoneTypes.
        """
        cleaned_reports = []
        for r in reports:
            # Convert the values of the report level keys.
            r = {k: [int(x) if x is not None else x for x in v] if k in
                 int_cols else v for k, v in r.items()}

            r = {k: [float(x) if x is not None else x for x in v] if k in
                 float_cols else v for k, v in r.items()}

            # Get the dict that contains expenses.
            exp = r[expenses_col]
            # Convert the values of the expense level keys.
            exp = {k: [int(x) if x is not None else x for x in v] if k in
                   int_cols else v for k, v in exp.items()}

            exp = {k: [float(x) if x is not None else x for x in v] if k in
                   float_cols else v for k, v in exp.items()}

            # Update the value for the `expenses_col` key.
            r[expenses_col] = exp

            # Add cleaned report dict to the list.
            cleaned_reports.append(r)

        return cleaned_reports


def main(userid, secret, template=None):
    """Instantiates Expensify class and fetches reports.

    Response format depends on `template`.

    Args:
        user_id (str): expensify api user id.
        secret (str): expensify api secret token.
        template (str): FreeMarker template for formatting request response.

    Returns:
        JSON: Expesnify reports. Output format depends on `template`.
    """
    if template is None:
        template = freemarker_templates.json_template
    ex = Expensify(userid, secret, template)
    reports = ex.reports()
    nullified_reports = Expensify.convert_missing_to_null(reports)
    cleaned_reports = Expensify.convert_data_types(nullified_reports)

    return cleaned_reports
