# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import logging
from bs4 import BeautifulSoup
import bs4
import urlparse
import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from xml.etree import ElementTree
_logger = logging.getLogger(__name__)


class Controllers(http.Controller):

    @http.route('/ebay/notification', type='http', auth="public", csrf=False, website=True)
    def ebay_notification(self, *arg, **kwargs):
        message = {}
        dump(request.httprequest)
        soup = BeautifulSoup(request.httprequest.data, "lxml")
        for r in soup.messages.contents[1].contents:
            if type(r) == bs4.element.Tag:
                message[r.name] = r.text
        message['UserInputtedText'] = BeautifulSoup(message['text'], "lxml").find(id='UserInputtedText').text
        message['rely_id'] = urlparse.parse_qs(urlparse.urlparse(message['responsedetails']).query)['messageid']
        headers = {'Content-Type': 'text/html'}
        response = request.make_response('', headers)
        response.status = '200'
        return response


def dump(obj):
    for attr in dir(obj):
        _logger.info("obj.%s = %r" % (attr, getattr(obj, attr)))
