odoo.define('stock_order_processing.PickDetails', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');
var Session = require('web.session');
var QWeb = core.qweb;
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

var _t = core._t;
var qz = window.qz;

var PickDetails = Widget.extend(BarcodeHandlerMixin, {
    template: 'op_pick_details',

    events: {
        "click .bypass_margin_warning_button": function(e) { this.bypass_margin_warning_clicked(e) },
        "click .button_skip": function(){ this.skip_pick() },
        "click .button_open_order": function(){ this.open_order() },
        "click .button_get_new_label": function(){ this.get_new_label() },
        "click .button_edit_dimensions": function(){ this.edit_dimensions() },
        "click .button_save_dimensions": function(){ this.save_dimensions() },
        "keyup input.op-dim-input.length": function(){ this.edit_length() },
        "keyup input.op-dim-input.width": function(){ this.edit_width() },
        "keyup input.op-dim-input.height": function(){ this.edit_height() },
        "keyup input.op-dim-input.weight": function(){ this.edit_weight() },
    },

    init: function (parent, pick_data, boxes, box_prices) {
        this._super.apply(this, arguments);
        BarcodeHandlerMixin.init.apply(this, arguments);
        this.pick_data = pick_data;
        this.boxes = boxes;
        this.state = 'in_progress';
        this.message = false;
        this.message_type = false;
        this.show_get_new_label = false;
        this.main_menu = parent;
        this.dimension_edit_mode = false;
        this.compute_display_missing_rate_error();
        // this.compute_display_margin_warning();
        this.box_prices = box_prices;
        this.display_package_warning = true;
        if (this.pick_data.packages.length > 0) {
            this.display_package_warning = false;
            this.compute_display_margin_warning();
        }
        this.renderElement();
    },

    on_barcode_scanned: function(barcode) {
        var self = this;

        if (self.state == 'done') {
            return;
        }
        self.message = false;
        self.message_type = false;

        // Check if there is missing rate or there is loss warning and if it is to be bypassed
        if (self.display_missing_rate_error || (self.display_margin_warning && !self.bypass_margin_warning)) {
            return;
        }

        // Check if barcode is for not requiring package

        if (barcode == 'no-box') {
            self.display_package_warning = false;
            self.pick_data.packaging_not_required = true;
            self.pick_data.packages = [];
            self.compute_display_margin_warning();
            self.renderElement();
            return;
        }

        // Check if barcode is for adding existing packaging line
        for (var i = 0, len = self.pick_data.packages.length; i < len; i++){
            if (self.pick_data.packages[i].barcode == barcode) {
                self.pick_data.packaging_not_required = false;
                self.pick_data.packages[i].quantity += 1;
                self.compute_display_margin_warning();
                self.renderElement();
                return;
            }
        }

        // Check if barcode is for adding new packaging line

        for (var i = 0, len = self.boxes.length; i < len; i++) {
            if (self.boxes[i].barcode == barcode || self.boxes[i].name == barcode) {
                self.pick_data.packages.push({barcode: barcode,
                    quantity: 1,
                    name: self.boxes[i].name,
                    packaging_product_id: self.boxes[i].product_variant_id[0],
                    id: self.boxes[i].id});
                self.pick_data.packaging_not_required = false;
                self.display_package_warning = false;
                self.compute_display_margin_warning();
                self.renderElement();
                return;
            }
        }

        if (!self.pick_data.packaging_not_required && self.pick_data.packages.length == 0) {
            self.message = 'Please enter packaging first.';
            self.message_type = 'error';
            self.renderElement();
            return;
        }

        for (var i = 0, len = self.pick_data.barcodes.length; i < len; i++){
            if (self.pick_data.ops[i].barcode === barcode || self.pick_data.ops[i].name == barcode) {
                self.pick_data.ops[i].qty_done += 1;
                self.renderElement();
            }
        }

        var invalid_barcode = _.every(self.pick_data.barcodes, function(b){
            return b != barcode;
        });

        if (invalid_barcode) {
            self.invalid_barcode = true;
            self.message = 'Invalid barcode.';
            self.message_type = 'error';
            self.renderElement();
        }

        var done = _.every(self.pick_data.ops, function(op){
            return op.qty_done >= op.qty_to_do;
        });
        if (done) {
            self.state = 'done';
            Session.rpc('/order_processing/done', {
                name: self.pick_data.name,
                packages: self.pick_data.packages,
                packaging_not_required: self.pick_data.packaging_not_required
            }).then(function(res) {
                if (res.tracking_number) {
                    self.show_get_new_label = true;
                    self.message = 'Pick successfully processed..';
                    self.message_type = 'success';
                    self.pick_data.carrier = res.carrier;
                    self.pick_data.service = res.service;
                    self.pick_data.tracking_number = res.tracking_number;
                    self.pick_data.rate = res.rate;
                    self.pick_data.label = res.label;
                    self.amz_order_type = res.amz_order_type;
                    self.print_shipping_label(res.label, res.amz_order_type);
                    self.main_menu.processed_counter.count += 1;
                    self.main_menu.processed_counter.renderElement();
                    self.main_menu.prime_orders_counter.update_count();
                } else if (res.warning) {
                    self.message = res.warning;
                    self.message_type = 'error';
                }
                self.renderElement();
            });
        }
    },

    compute_display_missing_rate_error: function() {
        if ( !(this.pick_data.rate > 0) ) {
            this.display_missing_rate_error = true;
        } else {
            this.display_missing_rate_error = false;
        }
    },

    compute_display_margin_warning: function() {
        var fee = 0;
        var pack_total_price = 0;
        for (var i = 0, len = this.pick_data.packages.length; i < len; i++) {
            for (var j = 0, ln = this.box_prices.length; j < ln; j++) {
                if (this.box_prices[j].id == this.pick_data.packages[i].id) {
                    pack_total_price += parseFloat(this.box_prices[j].price) * this.pick_data.packages[i].quantity;
                }
            }
        }
        if (this.pick_data.site == 'ebay') {
            fee = 0.89;
        } else {
            fee = 0.88;
        }
        if (this.pick_data
            && this.pick_data.rate >= 0
            && this.pick_data.total_product_cost >= 0
            && this.pick_data.total_sale_price >= 0
            && (fee * this.pick_data.total_sale_price) < (pack_total_price + this.pick_data.rate + this.pick_data.total_product_cost)
        ) {
            this.display_margin_warning = true;
            this.bypass_margin_warning = false;
            this.loss_amount = ((pack_total_price + this.pick_data.rate + this.pick_data.total_product_cost) - (fee * this.pick_data.total_sale_price)).toFixed(2);
        } else {
            this.display_margin_warning = false;
            this.bypass_margin_warning = true;
            this.loss_amount = 0;
        }
    },

    bypass_margin_warning_clicked: function(e) {
        e.preventDefault();
        this.bypass_margin_warning = true;
        this.renderElement();
    },

    skip_pick: function() {
        this.destroy();
    },

    open_order: function() {
        var self = this;
        Session.rpc('/order_processing/open_order', {
            name: self.pick_data.name,
        }).then(function(result) {
            if (result.action) {
                self.do_action(result.action);
            } else {
                self.message = 'Sale order not found.';
                self.message_type = 'error';
            }
        });
    },

    print_shipping_label: function(label, amz_order_type) {
        var self = this;
        qz.security.setCertificatePromise(function(resolve, reject) {
            $.ajax("/lable_zabra_printer/static/src/lib/d1.txt?foo").then(resolve, reject);
        });

        var privateKey = "-----BEGIN RSA PRIVATE KEY-----\n" +
        "MIIEoAIBAAKCAQEAtSDAfeqix4AWN4A2WrGBNEIZCb079/MfRhbULNRaZYDFO20d\n" +
        "00NJWjawaLEv1wz9tqhGdiZQKDoXvGpNNqhjkVbkEHF4S6Exa9ivlpCLPcU0dDrT\n" +
        "Lw6JxkHQuqv/5B8EgfhK9hXqEoHZQK64Mksp3l/vmqHG9lioj7eU/zyGyR0erkfE\n" +
        "bRNMtImoUbNuvSwkP67ZQHwMhk7ZqwNSGjA10OVnw78WN0gSvf03f6Ch6+LwrRbW\n" +
        "66ySk3WbNOcFUcWFUptT1jgLW2XaWQFJ5DcYmUFYwja8IV4Ol6johoblcuvQGQUR\n" +
        "ygkOGwwKv2jM8aOwLqG/UpT53I7Huebz/jPrAQIDAQABAoIBAA+WafpsHuYcV80e\n" +
        "846KiBv/NDhqWKbV/XMCs+/Htp/VnSOoGFD+EWn6GuRnmz5el9cIVEgGtA9CMJi+\n" +
        "bTau9yKi362qljer/5zQYQwMFG+UcRcvmM0L6z9smpH2C2eOY8zrmUfkSuic1B2E\n" +
        "68UoQsooZ25fTcgViSwVGHV+t/rGqbCOnr5o2+jT5TFDeT1KljiSLZX5XjxhoOSF\n" +
        "aQDIWdFoNLnTMZjelRyEhoZ+hDBFAdDeEHi1/yI3hjFlDPhdk8spzmlFDn/Y/5gd\n" +
        "ndDrGiN2yrQ1hfwL6GDPu68bSpVhazFvlhm54Op5nh7KXuQhVNifDpJ3eUdmKQH5\n" +
        "vp7ZkCECgYEA3h0zDWqGHz0LY25XOt/V19Ym7AKsUyy37OHciGWamqHkfuRPAq44\n" +
        "AyyJLGINNLnSGftwiHue7kcFjZgoTfQvMglLEQ6vwnK2tWBYSc/ZxVSc8e0G8hFB\n" +
        "8obXQNhRVjQ5YvdVKkE6P16hMBC2DQGh1qMNxzAm26kDMAoLP5jQsm8CgYEA0MLQ\n" +
        "et3k8pCOswro+tHoHRAvaLIOt0X8uPGI8V4Zqf3j8dvPa/PP4U+nd+olpHHrtKg2\n" +
        "xIHqbRg1knkDDqG8/Y5qVYWmby1WNIjyFNgLfACySI67IMcJY7/WiN4wCTkRibBE\n" +
        "cRj3uGNWfhFx2z1XgH33I0bUtgly4cHjqpCXMY8Cf3X/DSATdy0hQOuRssWUJAaF\n" +
        "viejQ+jr2Mn/MylC0N9VIg5HO7Iw25DUGAt8C4f3L6ad7SqUgdoT4N9X9hFzp57t\n" +
        "UPO+2aBzUJ0KkdykjwxF5xqe0RHIGUC+YZwRTyR8mf/5ZUUNYeRIYVknh49hTpi4\n" +
        "BpnK+tm27/qVW2RtynECgYAw/PZVTsrSDRAffbjsWuOgJlMpu1butRK4B53+Hfnh\n" +
        "xT1/XPiQuZcXpUyEPEL3EvCf5TVs6ZusXBj+NT19aoDh81CKnyFOR5JKI7TDJWuU\n" +
        "fslXc38AExTl/neGiLU3BNhTujRlYdmHwG/kh41zSDLHaUfcVFvIF/GIfqpBNUr1\n" +
        "iwKBgAKLb4u5g0CFEUnTxcg4ZOI8HN0lQDcnmYZ5gOXwlTWjfbpqp/u2kFMbVFmZ\n" +
        "HButkP7JzEhOcCK9RmN77wC7uJEeElFK0wrOwOFsjrucmvxQNFDAJzOI3tTkmJ9b\n" +
        "SeH3n6uVkawdsmjtst88/I36WpYTdVtxsdTfbD4kZ+6/N9eP\n" +
        "-----END RSA PRIVATE KEY-----";
        qz.security.setSignaturePromise(function(toSign) {
            return function(resolve, reject) {
                try {
                    var pk = new RSAKey();
                    pk.readPrivateKeyFromPEMString(strip(privateKey));
                    var hex = pk.signString(toSign, 'sha1');
                    console.log("DEBUG: \n\n" + stob64(hextorstr(hex)));
                    resolve(stob64(hextorstr(hex)));
                } catch (err) {
                    console.error(err);
                    reject(err);
                }
            };
        });

        function strip(key) {
            if (key.indexOf('-----') !== -1) {
                return key.split('-----')[2].replace(/\r?\n|\r/g, '');
            }
        }

        if (!qz.websocket.isActive()) {
            console.log('Waiting default');
            qz.websocket.connect().then(function() {
                console.log('Active success');
                self.find_printers(label, amz_order_type);
            });
        } else {
            console.log('An active connection with QZ already exists.', 'alert-warning');
            self.find_printers(label, amz_order_type);
        }
    },

    find_printers: function(label, amz_order_type) {
        var self = this;
        new Model('res.company').call('read', [self.session.company_id]).done(function(company) {
            qz.printers.find(company[0].shipping_printer).then(function(data) {
                 console.log("Found: " + data);
                 self.set_printer(data, label, amz_order_type);
             }).catch(function(err) {
             console.log("Found Printer Error:", err);
            });
        });
    },

    set_printer: function(printer, label, amz_order_type) {
        var self = this;
        var cfg = qz.configs.create(null);
        cfg.reconfigure({
            copies: 1,
        });
        cfg.setPrinter(printer);
        var print_type = 'pdf';
        if (amz_order_type === 'fbm') {
            print_type = 'image'
        }
        var printData = [{type: print_type, format: 'base64', data: label }];
        qz.print(cfg, printData).catch(function(e) { console.error(e); });
    },

    get_new_label: function() {
        var self = this;
        Session.rpc('/order_processing/get_new_label', {
            ship_id: self.pick_data.ship_id,
        }).then(function(result) {
            self.pick_data.tracking_lines.push({'tracking_number': result.tracking_number});
            self.print_shipping_label(result.label);
            self.renderElement();
        });
    },

    edit_dimensions: function() {
        var self = this;
        self.dimension_edit_mode = true;
        self.renderElement();
    },

    save_dimensions: function() {
        var self = this;
        self.dimension_edit_mode = false;
        new Model('stock.picking').call('update_dimension_from_order_processing_ui', [[self.pick_data.ship_id], {
            'length': parseFloat(self.pick_data.length),
            'width': parseFloat(self.pick_data.width),
            'height': parseFloat(self.pick_data.height),
            'weight': parseFloat(self.pick_data.weight),
        }]).done(function(data) {
            self.pick_data.carrier = data.carrier;
            self.pick_data.service = data.service;
            self.pick_data.rate = data.rate;
            self.compute_display_margin_warning();
            self.compute_display_missing_rate_error();
            self.renderElement();
        });
    },

    edit_length: function() {
        var self = this;
        self.pick_data.length = self.$('input.op-dim-input.length')[0].value;
    },

    edit_width: function() {
        var self = this;
        self.pick_data.width = self.$('input.op-dim-input.width')[0].value;
    },

    edit_height: function() {
        var self = this;
        self.pick_data.height = self.$('input.op-dim-input.height')[0].value;
    },

    edit_weight: function() {
        var self = this;
        self.pick_data.weight = self.$('input.op-dim-input.weight')[0].value;
    },
});

return PickDetails;

});


odoo.define('stock_order_processing.MainMenu', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');
var Session = require('web.session');
var QWeb = core.qweb;
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var PickDetails = require('stock_order_processing.PickDetails')

var _t = core._t;

var ProcessedCounter = Widget.extend({
    template: 'op_processed_counter',

    init: function(parent, count) {
        this._super.apply(this, arguments);
        this.count = count;
    }
});

var PrimeOrdersCounter = Widget.extend({
    template: 'op_prime_orders_counter',

    init: function(parent, count) {
        this._super.apply(this, arguments);
        this.count = count;
    },

    update_count: function () {
        var self = this;
        new Model('stock.picking').call('get_prime_orders_count').then(function(data) {
            self.count = data.count;
            self.renderElement();
        });
    }
});

var LateCounter = Widget.extend({
    template: 'op_late_counter',

    init: function(parent, count) {
        this._super.apply(this, arguments);
        this.count = count;
    }
});

var MainMenu = Widget.extend(BarcodeHandlerMixin, {
    template: 'order_processing_main_menu',

    events: {
        "click .processed_counter_container": function(){ this.open_processed_orders() },
        "click .prime_orders_counter_container": function(){ this.open_prime_orders() },
        "click .late_counter_container": function(){ this.open_late_orders() },
    },

    init: function(parent, action) {
        this._super;
        BarcodeHandlerMixin.init.apply(this, arguments);
    },

    start: function () {
        var self = this;
        this.pick_details_container = this.$('.op_pick_details_container');
        new Model('product.template').query(['name', 'barcode', 'product_variant_id'])
           .filter([['is_packaging_product', '=', true]])
           .all()
           .then(function (boxes){
                self.boxes = boxes;
            });
        Session.rpc('/order_processing/get_box_prices', {}).then(function (box_prices) {
            self.box_prices = box_prices;
        });
        new Model('stock.picking').call('get_processed_orders_count').then(function(data) {
            self.processed_counter = new ProcessedCounter(self, data.count);
            self.processed_counter.appendTo(self.$('.processed_counter_container'));
        });
        new Model('stock.picking').call('get_prime_orders_count').then(function(data) {
            self.prime_orders_counter = new PrimeOrdersCounter(self, data.count);
            self.prime_orders_counter.appendTo(self.$('.prime_orders_counter_container'));
        });
        new Model('stock.picking').call('get_late_orders_count').then(function(data) {
            self.late_orders_counter = new LateCounter(self, data.count);
            self.late_orders_counter.appendTo(self.$('.late_counter_container'));
        });
        return this._super.apply(this, arguments);
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        if (barcode && !self.pick_details || self.pick_details.isDestroyed() || self.pick_details.state == 'done') {
            Session.rpc('/order_processing', {
                barcode: barcode,
            }).then(function(pick_data) {
                if (pick_data.name) {
                    if (self.pick_details) {
                        self.pick_details.destroy();
                    }
                    self.pick_details = new PickDetails(self, pick_data, self.boxes, self.box_prices);
                    self.pick_details.appendTo(self.pick_details_container);
                } else if (pick_data.warning) {
                    self.do_warn(pick_data.warning);
                }
            });
        }
    },

    open_processed_orders: function() {
        var self = this;
        Session.rpc('/order_processing/open_processed_orders').then(function(result) {
            if (result.action) {
                self.do_action(result.action);
            }
        });
    },

    open_prime_orders: function() {
        var self = this;
        Session.rpc('/order_processing/open_prime_orders').then(function(result) {
            if (result.action) {
                self.do_action(result.action);
            }
        });
    },

    open_late_orders: function() {
      var self = this;
      Session.rpc('/order_processing/open_late_orders').then(function(result) {
          if (result.action) {
              self.do_action(result.action);
          }
      });
    }

});

core.action_registry.add('stock_order_processing_main_menu', MainMenu);

return {
    MainMenu: MainMenu,
};

});
