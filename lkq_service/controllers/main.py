# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from odoo import http
from odoo.http import request
import logging
import zipfile

_logger = logging.getLogger(__name__)


class LKQService(http.Controller):
    @http.route('/lkq/invoices', type='http', auth="public", csrf=False, website=True)
    def LKQ_invoices(self, *arg, **kwargs):
        try:
            _logger.info('LKQ_CALL arg: %s', arg)
        except:
            pass
        try:
            _logger.info('LKQ_CALL kwargs: %s', kwargs)
            if kwargs.get('file'):
                fs = kwargs['file']
                path = '/tmp/' + fs.filename
                fs.save(path)
                zip_ref = zipfile.ZipFile(path, 'r')
                zip_ref.extractall('/tmp/')
                zip_ref.close()
                f = open('/tmp/' + zip_ref.infolist()[0].filename)
                r = f.readlines()
                for l in r:
                    _logger.info(l)
                f.close()
        except:
            pass
        try:
            _logger.info('LKQ_CALL request: %s', request)
        except:
            pass
        try:
            _logger.info('LKQ_CALL request.httprequest: %s', request.httprequest)
        except:
            pass
        try:
            _logger.info('LKQ_CALL request.httprequest.data: %s', request.httprequest.data)
        except:
            pass
        try:
            soup = BeautifulSoup(request.httprequest.data, "lxml")
            _logger.info('LKQ_CALL soup: %s', soup)
        except:
            pass
        try:
            _logger.info('LKQ_CALL dump:')
            dump(request)
        except:
            pass
        headers = {'Content-Type': 'text/html'}
        response = request.make_response('', headers)
        response.status = '200'
        return response


def dump(obj):
    for attr in dir(obj):
        _logger.info("obj.%s = %r" % (attr, getattr(obj, attr)))
