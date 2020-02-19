# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import logging
from slackclient import SlackClient


class MyHandler(logging.Handler):
    slack_bot_token = 'xoxb-312554961652-uSmliU84rFhnUSBq9YdKh6lS'
    # slack_channel_id = 'U8H76NQDR'  # slackbot
    slack_channel_id = 'CAMH1MT8D'  # _odoo_errors
    slack_odoo_warnings_channel_id = 'CF4RM6EJY'  # _odoo_warnings
    sc = SlackClient(slack_bot_token)

    def emit(self, record):
        if record:
            if record.levelname in ['ERROR']:
                text = ''
                if record.exc_text:
                    text = record.exc_text
                elif record.message:
                    text = record.message
                # if 'bus.Bus only string channels are allowed.' in text:
                #     return
                # if 'bus.Bus unavailable' in text:
                #     return
                self.sc.api_call("chat.postMessage",
                                 channel=self.slack_channel_id,
                                 as_user=False,
                                 username=record.levelname + ' at: ' + record.asctime if hasattr(record, 'asctime') else record.levelname,
                                 text=text)
            elif record.levelname in ['WARNING']:
                text = ''
                if record.exc_text:
                    text = record.exc_text
                elif record.message:
                    text = record.message
                self.sc.api_call("chat.postMessage",
                                 channel=self.slack_odoo_warnings_channel_id,
                                 as_user=False,
                                 username=record.levelname + ' at: ' + record.asctime if hasattr(record, 'asctime') else record.levelname,
                                 text=text)


mh = MyHandler()
logging.getLogger().addHandler(mh)


class SlackCalls(models.TransientModel):
    _name = 'slack.calls'

    @api.model
    def notify_slack(self, source, message, channel_id=None, attachment=None):
        slack_bot_token = self.env['ir.config_parameter'].get_param('slack_bot_token')
        # slack_cron_info_channel_id = self.env['ir.config_parameter'].get_param('slack_cron_info_channel_id')
        if not channel_id:
            channel_id = self.env['ir.config_parameter'].get_param('slack_odoo_cron_info_channel_id')
        sc = SlackClient(slack_bot_token)
        sc.api_call("chat.postMessage",
                    channel=channel_id,
                    as_user=False,
                    username=source,
                    text=message,
                    attachments=[attachment])
