import ast
import json
import requests
import time


class Expensify(object):
    _url = "https://integrations.expensify.com/Integration-Server/ExpensifyIntegrations"

    _template = """
    [<#compress><#lt>
        <#list reports as report>
            <#if report.reportName?contains("%s")>
            <#if report?has_next>
                {<#t>
                    "id": "${report.reportID}",<#t>
                    "name": "${report.reportName}"<#t>
                },<#t>
            <#else>
                {<#t>
                    "id": "${report.reportID}",<#t>
                    "name": "${report.reportName}"<#t>
                }<#t>
            </#if>
            </#if><#t>
        </#list><#t></#compress>]"""

    def __init__(self, userid, secret):
        self._userid = userid
        self._secret = secret

    def reports(self, reportname, start_timestamp=None):
        """Requests all reports whose name contains `reportname` and
        where the report was created or updated after `start_timestamp`,
        which is optional and defaults to 30 days ago.
        Returns a dict of reports, keyed on the report ID."""

        if start_timestamp is None:
            # Assume a month ago.
            start_timestamp = time.time() - (24 * 3600 * 30)

        report_filename = self._generate_report(reportname, start_timestamp)
        report = self._fetch_file(report_filename)
        return report #yaml.BaseLoader(report)

    def _generate_report(self, reportname, start_timestamp):
        """Requests all reports whose name contains `reportname` and
        where the report was created or updated after `start_timestamp`,
        Returns a filename which should be fed to _fetch_file."""

        params = {
            "requestJobDescription": json.dumps({
            "type": "file",
            "credentials": {
                "partnerUserID": self._userid,
                "partnerUserSecret": self._secret
            },
            "onReceive":{
                "immediateResponse":["returnRandomFileName"]
            },
            "inputSettings":{
                "type":"combinedReportData",
                "filters": {
                    "startDate": time.strftime("%Y-%m-%d", time.gmtime(start_timestamp)) 
                }
            },
            "outputSettings":{
                "fileExtension":"json",
                "fileBasename":"the_expensify_api_is_horrible_to_code_against_"
            }
            }),
            "template": self._template % reportname
        }

        response = requests.get(self._url, params=params)
        response_content = response.content
        return_response = response_content.decode('ascii')

        if response.content.endswith(b".json"):
            return return_response
        else:
            raise RuntimeError("Failed to generate Expensify report, their API responded with %s" % response.content)

    def _fetch_file(self, filename):
        """Given a `filename`, fetch it from Expensify."""
        params = {
            "requestJobDescription": json.dumps({
                "type": "download",
                "credentials": {
                    "partnerUserID": self._userid,
                    "partnerUserSecret": self._secret,
                },
                "fileName": str(filename)
                })
            }

        response = requests.get(self._url, params=params)

        response_content = response.content
        return_response = response_content.decode('utf-8')
        return_response = ast.literal_eval(return_response)

        if response.status_code == 200:
            return return_response
        else:
            raise RuntimeError("Failed to fetch a file from Expensify, "
                               "their API responded with: "
                               "%s" % response.content)


def main(userid, secret):
    ex = Expensify(userid, secret)
    reports = ex.reports("James")

    return reports