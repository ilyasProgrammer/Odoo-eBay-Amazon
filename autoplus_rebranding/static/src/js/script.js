odoo.define('autoplus_rebranding', function (require) {
"use strict";

var core = require('web.core');
var WebClient = require('web.WebClient');

var utils = require('web.utils');

var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

    WebClient.include({
        init: function(parent, client_options) {
            this.client_options = {};
            this._super(parent);
            this.origin = undefined;
            if (client_options) {
                _.extend(this.client_options, client_options);
            }
            this._current_state = null;
            this.menu_dm = new utils.DropMisordered();
            this.action_mutex = new utils.Mutex();
            this.set('title_part', {"zopenerp": "Opsyst"});
        }
    });
});