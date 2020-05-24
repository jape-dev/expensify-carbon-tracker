"""FreeMarker template for making requests to the Expensify API."""

json_template = """
[<#compress><#lt>
    <#list reports as report>
        {<#t>
            "report_id": ${report.reportID},<#t>
            "report_name": "${report.reportName}",<#t>
            "report_policy_id": "${report.policyID}",<#t>
            "report_expenses": {
                <#assign id_seq = []>
                <#assign type_seq = []>
                <#assign cat_seq = []>
                <#assign amt_seq = []>
                <#assign curr_seq = []>
                <#assign comm_seq = []>
                <#assign conv_amt_seq = []>
                <#assign created_seq = []>
                <#assign insrt_seq = []>
                <#assign merch_seq = []>
                <#assign mod_amt_seq = []>
                <#assign mod_created_seq = []>
                <#assign mod_merch_seq = []>
                <#assign unit_count_seq = []>
                <#assign unit_rate_seq = []>
                <#assign unit_unit_seq = []>
                <#list report.transactionList as expense>
                    <#assign id_seq += [expense.transactionID]>
                    <#assign type_seq += [expense.type]>
                    <#assign cat_seq += [expense.category]>
                    <#assign amt_seq += [expense.amount]>
                    <#assign curr_seq += [expense.currency]>
                    <#assign comm_seq += [expense.comment]>
                    <#assign conv_amt_seq += [expense.convertedAmount]>
                    <#assign created_seq += [expense.created]>
                    <#assign insrt_seq += [expense.inserted]>
                    <#assign merch_seq += [expense.merchant]>
                    <#assign mod_amt_seq += [expense.modifiedAmount]>
                    <#assign mod_created_seq += [expense.modifiedCreated]>
                    <#assign mod_merch_seq += [expense.modifiedMerchant]>
                    <#assign unit_count_seq += [expense.units.count	]>
                    <#assign unit_rate_seq += [expense.units.rate]>
                    <#assign unit_unit_seq += [expense.units.rate]>
                </#list>
                "expense_id": [<#list id_seq as i>"${i}"<#sep>, </#list>],
                "expense_type": [<#list type_seq as i>"${i}"<#sep>, </#list>],
                "expense_category": [<#list cat_seq as i>"${i}"<#sep>, </#list>],
                "expense_amount": [<#list amt_seq as i>"${i}"<#sep>, </#list>],
                "expense_currency": [<#list curr_seq as i>"${i}"<#sep>, </#list>],
                "expense_comment": [<#list comm_seq as i>"${i}"<#sep>, </#list>],
                "expense_converted_amount": [<#list conv_amt_seq as i>"${i}"<#sep>, </#list>],
                "expense_created_date": [<#list created_seq as i>"${i}"<#sep>, </#list>],
                "expense_inserted_date": [<#list insrt_seq as i>"${i}"<#sep>, </#list>],
                "expense_merchant": [<#list merch_seq as i>"${i}"<#sep>, </#list>],
                "expense_modified_amount": [<#list mod_amt_seq as i>"${i}"<#sep>, </#list>],
                "expense_modified_created_date": [<#list mod_created_seq as i>"${i}"<#sep>, </#list>],
                "expense_modified_merchant": [<#list mod_merch_seq as i>"${i}"<#sep>, </#list>],
                "expense_unit_count": [<#list unit_count_seq as i>"${i}"<#sep>, </#list>],
                "expense_unit_rate": [<#list unit_rate_seq as i>"${i}"<#sep>, </#list>],
                "expense_unit_unit": [<#list unit_unit_seq as i>"${i}"<#sep>, </#list>]
            }<#t>
        }<#t>
        <#if report?has_next>,</#if><#t>
    </#list><#t></#compress>]"""
