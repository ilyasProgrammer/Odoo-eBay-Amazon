odoo.define('returns_management.MainMenu', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');
var Session = require('web.session');
var QWeb = core.qweb;
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

var _t = core._t;

var MainMenu = Widget.extend(BarcodeHandlerMixin, {
    template: 'returns_processing_main_menu',

    events: {
        "click .button_scrap": 'scrap_items',
    },

    init: function(parent, action) {
        this._super.apply(this, arguments);
        BarcodeHandlerMixin.init.apply(this, arguments);
        this.got_item_scanned = false;
        this.directive = 'Scan return label barcode';
        this.ret_data = {};
        this.renderElement();
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments);
    },

    on_barcode_scanned: function (barcode) {
        var self = this;
        $('.button_scrap').hide();
        var popup = document.getElementById("error_msg");
        Session.rpc('/return_barcode_scanned', {
            barcode: barcode,
        }).then(function (ret_data) {
            if (ret_data.type == 'return') {
                self.got_item_scanned = true;
                self.ret_data.id = ret_data.id;
                self.ret_data.web_order_id = ret_data.web_order_id;
                self.ret_data.tracking_number = ret_data.tracking_number;
                self.ret_data.carrier_name = ret_data.carrier_name;
                self.ret_data.product_name = ret_data.product_name;
                self.ret_data.lad = ret_data.lad;
                self.ret_data.customer_comments = ret_data.customer_comments;
                self.ret_data.return_reason = ret_data.return_reason;
                self.directive = 'Now scan location barcode';
                self.renderElement();
                $('.button_scrap').show();
            } else if (ret_data.type == 'location') {
                if (self.got_item_scanned == false){
                    popup.innerHTML = 'Scan item label first';
                    $('#error_msg').fadeIn(200);
                    return
                }
                self.directive = 'Scan return label barcode';
                self.got_item_scanned = false;
                self.ret_data.location_barcode = ret_data.barcode;
                self.renderElement();
                self.receive_item(ret_data);
            } else if (ret_data.warning) {
                self.got_item_scanned = false;
                self.do_warn(ret_data.warning);
                self.renderElement();
            } else if (ret_data.error) {
                self.got_item_scanned = false;
                popup.innerHTML = ret_data.error;
                $('#error_msg').fadeIn(200);
            }
        });

    },
    receive_item: function (ret_data) {
        var self = this;
        var error_msg = document.getElementById("error_msg");
        Session.rpc('/return_receive_item', {
            ret_data: self.ret_data
        }).then(function (resp) {
            if (resp.message == 'received') {
                var popup = document.getElementById("received_msg");
                popup.textContent = 'Received to ' + ret_data.name;
                $('#received_msg').fadeIn(400).delay(2000).fadeOut(400);
            } else if (resp.message == 'no_pickings') {
                self.got_item_scanned = false;
                error_msg.innerHTML = 'No pickings';
                $('#error_msg').fadeIn(200);
            } else if (resp.warning) {
                self.do_warn(ret_data.warning);
                self.renderElement();
            }

        });
    },

    scrap_items: function() {
        var self = this;
        Session.rpc('/return_scrap_items', {
            ret_data: self.ret_data
        }).then(function (resp) {
            self.got_item_scanned = false;
            self.directive = 'Scan return label barcode';
            self.ret_data = {};
            self.renderElement();
            if (resp.message == 'scrapped') {
                var popup = document.getElementById("received_msg");
                popup.textContent = 'Scrapped';
                $('#received_msg').fadeIn(400).delay(2000).fadeOut(400);
            }else{
                var popup = document.getElementById("received_msg");
                popup.textContent = resp.error;
                $('#error_msg').fadeIn(400).delay(2000).fadeOut(400);
            }
        });
    },

});
core.action_registry.add('returns_management_main_menu', MainMenu);

return {
    MainMenu: MainMenu,
};

});
