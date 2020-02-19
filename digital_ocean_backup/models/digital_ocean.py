# -*- coding: utf-8 -*-
import urllib
import urllib2
import json
import random

from odoo import api, fields, models


class DigitalOcean(models.Model):
    _name = 'digital.ocean'
    _rec_name = 'token_id'

    token_name = fields.Char(required="True")
    token_id = fields.Char('Token ID', required="True")
    droplet_line_ids = fields.One2many('digital.ocean.droplet', 'digitalocean_token')

    @api.multi
    def get_droplets(self):
        for record in self:
            url = 'https://api.digitalocean.com/v2/droplets'
            request = urllib2.Request(url)
            request.add_header("Authorization", "Bearer %s" % record.token_id)
            result = urllib2.urlopen(request)
            resonse = json.load(result)
            droplets = resonse.get('droplets')
            if droplets:
                droplet_obj = self.env['digital.ocean.droplet']
                for droplet in droplets:
                    exisiting_droplet = droplet_obj.search([('droplet_id', '=', droplet.get('id'))])
                    if not exisiting_droplet:
                        droplet_obj.create({
                            'digitalocean_token': record.id,
                            'droplet_id': droplet.get('id'),
                            'droplet_name': droplet.get('name'),
                            'droplet_size': droplet.get('memory'),
                            'droplet_region': droplet.get('region').get('slug'),
                            'droplet_image_distribution': droplet.get('image').get('distribution'),
                            'droplet_image_name': droplet.get('image').get('name'),
                            'droplet_status': droplet.get('status'),
                        })



class DigitalOceanDroplet(models.Model):
    _name = 'digital.ocean.droplet'
    _rec_name = 'droplet_name'
    _description = "Digital Ocean Droplet"

    def _get_default_cron_id(self):
        return self.env['ir.cron'].search([('name', '=', 'Auto Snapshot Digital Ocean'), ('model', '=', 'digital.ocean.droplet')]).id

    digitalocean_token = fields.Many2one('digital.ocean', string="Digital Ocean Token")
    droplet_id = fields.Char(string="Droplet ID", required=True)
    droplet_name = fields.Char(string="Name", required=True)
    droplet_size = fields.Float(string="Size", required=True)
    droplet_region = fields.Char(string="Region", required=True, help="The unique slug identifier for the region that you wish to deploy in.")
    droplet_status = fields.Char(string="Status")
    droplet_image_distribution = fields.Char(string="Image Distributer")
    droplet_image_name = fields.Char(string="Image Distributer Version")
    autosnapshot = fields.Boolean(string="Auto Backup ?")
    cron_id = fields.Many2one('ir.cron', string="Cron ID", readonly=True, default=_get_default_cron_id)
    snapshot_line_ids = fields.One2many('digital.ocean.snapshot', 'digital_ocean_droplet', string="Snapshot Lines")

    @api.model
    def run(self):
        droplets = self.env['digital.ocean.droplet'].search([('autosnapshot', '=', True)])
        for droplet in droplets:
            droplets.create_snapshot()

    @api.multi
    def create_snapshot(self):
        for record in self:
            if record.digitalocean_token and record.droplet_id:
                url = 'https://api.digitalocean.com/v2/droplets/%s/actions' % record.droplet_id
                random_no = str(random.randint(0,9)) + str(random.randint(0,9)) + str(random.randint(0,9)) + str(random.randint(0,9)) + str(random.randint(0,9)) + str(random.randint(0,9))
                snapshot_name = "%s/%s/%s" % (random_no, record.droplet_id, fields.Datetime.now())
                values = {
                  "type": "snapshot",
                  "name": snapshot_name
                }
                data = urllib.urlencode(values)
                request = urllib2.Request(url, data)
                request.add_header("Authorization", "Bearer %s" % record.digitalocean_token.token_id)
                result = urllib2.urlopen(request)
                response = json.load(result)
                snapshot = response.get('action')
                if snapshot.get('id') and snapshot.get('status') and snapshot.get('resource_id'):
                    self.env['digital.ocean.snapshot'].create({
                        'name': snapshot_name,
                        'digital_ocean_droplet': record.id
                    })

    @api.multi
    def update_snapshot(self):
        for record in self:
            url = 'https://api.digitalocean.com/v2/snapshots'
            request = urllib2.Request(url)
            request.add_header("Authorization", "Bearer %s" % record.digitalocean_token.token_id)
            result = urllib2.urlopen(request)
            response = json.load(result)
            snapshots = response.get('snapshots')
            if not snapshots:
                [item.unlink() for item in record.snapshot_line_ids] and record.snapshot_line_ids
            if snapshots:
                [item.unlink() for item in record.snapshot_line_ids] and record.snapshot_line_ids
                for snapshot in snapshots:
                    if snapshot.get('resource_id') == record.droplet_id:
                        self.env['digital.ocean.snapshot'].create({
                            'name': snapshot.get('name'),
                            'digital_ocean_droplet': self.env['digital.ocean.droplet'].search([('droplet_id', '=', snapshot.get('resource_id'))]).id
                        })


class DigitalOceanSnapshot(models.Model):
    _name = 'digital.ocean.snapshot'

    name = fields.Char(required=True)
    digital_ocean_droplet = fields.Many2one('digital.ocean.droplet', string="Droplet")


