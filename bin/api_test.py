
import requests
import time
import json

# These are not your normal Expensify login credentials. You can find your
# 'integration' credentials by visiting https://www.expensify.com/tools/integrations/
# while logged in.

class Expensify(object):
    _url = "https://integrations.expensify.com/Integration-Server/ExpensifyIntegrations"

    # The template language is FreeMarker, documented at http://freemarker.org/
    # Some of the available fields are (badly) documented in https://github.com/Expensify/Integrations/blob/master/templates/everything_csv.fm
    _template = """reports:
<#list reports as report>
  <#if report.reportName?contains("%s")>
  ${report.reportID}:
    name: ${report.reportName}
    transactions:
    <#list report.transactionList as expense>
      - id: ${expense.transactionID}
        details: ${expense.details}
        inserted: ${expense.inserted}
        tag: ${expense.tag}
        currency: ${expense.currency}
        convertedAmount: ${expense.convertedAmount}
        currencyConversionRate: ${expense.currencyConversionRate}
        category: ${expense.category}
        comment: ${expense.comment}
        <#if expense.modifiedMerchant?has_content>
        merchant: ${expense.modifiedMerchant}
        <#else>
        merchant: ${expense.modifiedMerchant}
        </#if>
        <#if expense.modifiedAmount?has_content>
        amount: ${expense.modifiedAmount}
        <#else>
        amount: ${expense.amount}
        </#if>
        <#if expense.modifiedCreated?has_content>
        created: ${expense.modifiedCreated}
        <#else>
        created: ${expense.created}
        </#if>
        <#if expense.receiptObject?has_content>
        receipt:
          image: ${expense.receiptObject.url!}
          thumbnail: ${expense.receiptObject.thumbnail!}
          smallthumbnail: ${expense.receiptObject.smallThumbnail!}
          state: ${expense.receiptObject.state!}
          receiptid: ${expense.receiptObject.receiptID!}
          formattedamount: ${expense.receiptObject.formattedAmount!}
        </#if>
  </#list>
  </#if>
</#list>"""

    def __init__(self, userid, secret):
        self._userid = userid
        self._secret = secret

    def reports(self, reportname, start_timestamp = None):
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
                        "fileExtension":"txt",
                        "fileBasename":"the_expensify_api_is_horrible_to_code_against_"
                    }
                }),
            "template": self._template % reportname
        }

        response = requests.get(self._url, params = params)
        response_content = response.content
        return_response = response_content.decode('ascii')

        if response.content.endswith(b".txt"):
            return return_response
        else:
            raise RuntimeError("Failed to generate Expensify report, their API responded with %s" % response.content)

    def _fetch_file(self, filename):
        """Given a `filename`, fetch it from Expensify."""
        params = {
            "requestJobDescription": json.dumps({
                "type":"download",
                "credentials":{
                    "partnerUserID": self._userid,
                    "partnerUserSecret": self._secret,
                },
                "fileName": str(filename)
                })
            }
    
        response = requests.get(self._url, params = params)
        
        if response.status_code == 200:
            return response.content
        else:
            raise RuntimeError("Failed to fetch a file from Expensify, their API responded with: %s" % response.content)
    

if __name__ == '__main__':
    userid = ""
    secret = ""

    ex = Expensify(userid, secret)
    reports = ex.reports("James")
    print(f"Report: \n {reports}")