
test_content1 = """

Dear Theoria International,

A customer has requested to return the item(s) listed below and the request is auto authorized as per the return policies.

Order ID: # 114-3395583-5482613
Item: Make Auto Parts Manufacturing - X5 14-15 FRONT BUMPER MOLDING RH, Grille Cover, Chrome w/o M Sport Line, Type 1, Luxury Line - BM1039153
Quantity: 2
Return reason: Couldn't install

Item: Make Auto Parts Manufacturing - X5 14-15 FRONT BUMPER MOLDING LH, Grille Cover, Chrome w/o M Sport Line, Type 1, Luxury Line - BM1038153
Quantity: 1
Return reason: Couldn't install

Return Shipping Carrier:  UPS
Tracking ID: 1Z30033A9009145478
Request received: May 24, 2017
"""

test_content2 = """

Dear Theoria International,

A customer has requested to return the item(s) listed below and the request is auto authorized as per the return policies.

Order ID: # 113-4579443-5124268
Item: Make Auto Parts Manufacturing - PASSAT 12-15 FRONT BUMPER COVER, Primed Black - VW1000199
Quantity: 1
Return reason: Didn't approve purchase
Customer comments: I emailed because when I first purchased item my payment did not clear. I'd like for the seller to pay for returning shipping. Very frustrated after first order didn't go through, I cancelled order.

Return Shipping Carrier:  UPS
Tracking ID: 1Z30033A9009144308
Request received: May 24, 2017
"""

test_content3 = """<div dir="ltr"><span style="font-size:12.8px">Dear Theoria International,</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">A customer has requested to return the item(s) listed below and the request is auto authorized as per the return policies.</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Order ID: # 114-3395583-5482613</span><br style="font-size:12.8px"><span style="font-size:12.8px">Item: Make Auto Parts Manufacturing - X5 14-15 FRONT BUMPER MOLDING RH, Grille Cover, Chrome w/o M Sport Line, Type 1, Luxury Line - BM1039153</span><br style="font-size:12.8px"><span style="font-size:12.8px">Quantity: 2</span><br style="font-size:12.8px"><span style="font-size:12.8px">Return reason: Couldn&#39;t install</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Item: Make Auto Parts Manufacturing - X5 14-15 FRONT BUMPER MOLDING LH, Grille Cover, Chrome w/o M Sport Line, Type 1, Luxury Line - BM1038153</span><br style="font-size:12.8px"><span style="font-size:12.8px">Quantity: 1</span><br style="font-size:12.8px"><span style="font-size:12.8px">Return reason: Couldn&#39;t install</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Return Shipping Carrier:\xa0 UPS</span><br style="font-size:12.8px"><span style="font-size:12.8px">Tracking ID: 1Z30033A9009145478</span><br style="font-size:12.8px"><span style="font-size:12.8px">Request received: May 24, 2017</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Return request details:</span><br style="font-size:12.8px"><a href="https://sellercentral.amazon.com/gp/returns/list?searchType=rma&amp;keywordSearch=DsZC55PnRRMA&amp;salesChannelFilter=sitesall&amp;preSelectedRange=exactDates&amp;exactFromDate=5/25/2017&amp;exactToDate=5/25/2017&amp;stateIds=Approved&amp;stateIds=Approving" rel="noreferrer" target="_blank" style="font-size:12.8px">https://sellercentral.amazon.<wbr>com/gp/returns/list?<wbr>searchType=rma&amp;keywordSearch=<wbr>DsZC55PnRRMA&amp;<wbr>salesChannelFilter=sitesall&amp;<wbr>preSelectedRange=exactDates&amp;<wbr>exactFromDate=<span class="gmail-aBn"><span class="gmail-aQJ">5/25/2017</span></span>&amp;<wbr>exactToDate=<span class="gmail-aBn"><span class="gmail-aQJ">5/25/2017</span></span>&amp;<wbr>stateIds=Approved&amp;stateIds=<wbr>Approving</a><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Order details:</span><br style="font-size:12.8px"><a href="https://sellercentral.amazon.com/gp/orders-v2/details/ref=ag_orddet_cont_myo?ie=UTF8&amp;orderID=114-3395583-5482613" rel="noreferrer" target="_blank" style="font-size:12.8px">https://sellercentral.amazon.<wbr>com/gp/orders-v2/details/ref=<wbr>ag_orddet_cont_myo?ie=UTF8&amp;<wbr>orderID=114-3395583-5482613</a><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Contact the customer about the return request:</span><br style="font-size:12.8px"><a href="https://sellercentral.amazon.com/gp/orders-v2/contact?orderID=114-3395583-5482613" rel="noreferrer" target="_blank" style="font-size:12.8px">https://sellercentral.amazon.<wbr>com/gp/orders-v2/contact?<wbr>orderID=114-3395583-5482613</a><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">To learn more about managing returns, visit the Manage Returns tool in your seller account and click &quot;Video tutorials&quot;:</span><br style="font-size:12.8px"><a href="https://sellercentral.amazon.com/gp/returns" rel="noreferrer" target="_blank" style="font-size:12.8px">https://sellercentral.amazon.<wbr>com/gp/returns</a><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Sincerely,</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Amazon Services</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Please note: This e-mail message was sent from a notification-only address that cannot accept incoming e-mail. Please do not reply to this message.</span><br style="font-size:12.8px"><br style="font-size:12.8px"><span style="font-size:12.8px">Was this email helpful?</span><br style="font-size:12.8px"><span style="font-size:12.8px">\xa0</span><a href="https://sellercentral.amazon.com/gp/satisfaction/survey-form.html?ie=UTF8&amp;HMDName=NotificationBusEmailHMD&amp;customAttribute1Value=RETURN_REQUEST" rel="noreferrer" target="_blank" style="font-size:12.8px">https://sellercentral.amazon.<wbr>com/gp/satisfaction/survey-<wbr>form.html?ie=UTF8&amp;HMDName=<wbr>NotificationBusEmailHMD&amp;<wbr>customAttribute1Value=RETURN_<wbr>REQUEST</a><br></div>\n
"""


content = test_content3.split('\n')
if len(content)< 5:
    content = test_content3.split('\r\n')
if len(content)< 5:
    test_content3 = test_content3.replace('<br style="font-size:12.8px">','').replace('</span>','')
    content = test_content3.split('<span style="font-size:12.8px">')
values = {'lines': []}
searchstrings = [
    ['web_order_id', 'Order ID: # '], 
    ['item', 'Item: '], 
    ['product_uom_qty', 'Quantity: '],
    ['return_reason', 'Return reason: '], 
    ['customer_comments', 'Customer comments: '], 
    ['carrier_id', 'Return Shipping Carrier:  '], 
    ['tracking_number', 'Tracking ID: '], 
    ['request_date', 'Request received: ']
]
for line in content:
    for searchstring in searchstrings:
        if line.startswith(searchstring[1]):
            val = line[len(searchstring[1]):]
            if searchstring[0] == "item":
                values['lines'].append({'item': val})
            elif searchstring[0] == "product_uom_qty":
                values['lines'][-1]['product_uom_qty'] = float(val)
            elif searchstring[0] == "return_reason":
                values['lines'][-1]['return_reason'] = val
            elif searchstring[0] == "customer_comments":
                values['lines'][-1]['customer_comments'] = val
            elif searchstring[0] == "carrier_id":
                print val
            else:
                values[searchstring[0]] = line[len(searchstring[1]):]
            break
    else:
        print line
lines = values['lines']
values.pop('lines')
print values
print lines

# "id", "product_uom_qty", "product_id", "sale_line_id", "return_reason", "return_id", "customer_comments", "item", "product_uom", "create_uid", "write_uid", "create_date", "write_date") VALUES(
#
# nextval('sale_return_line_id_seq'),
# '1.000',
# 62,
# 116,
# 'Bought wrong part',
# 36,
# 'wrong one',
# 'Chevy S10 Pickup Pick Up Truck 82-90 Front Grille Grill Car Black', 1, 1, 1, (now() at time zone 'UTC'), (now() at time zone 'UTC'))