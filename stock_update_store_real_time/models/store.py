# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import math
import logging

_logger = logging.getLogger(__name__)


class Store(models.Model):
    _inherit = 'sale.store'

    repricer_scheme_id = fields.Many2one('repricer.scheme', 'Repricer Scheme')


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return ret_type
    return data