odoo.define('stock_scan_lad.Item', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var Session = require('web.session');

var Item = Widget.extend(BarcodeHandlerMixin, {
    template: 'scan_lad_item',
    events: {
        "click #print_label": function(){ this.print_label() },
    },

    init: function(parent, item) {
        this._super.apply(this, arguments);
        BarcodeHandlerMixin.init.apply(this, arguments);
        this.item = item;
        this.id = item.id;
        this.name = item.name;
        this.mfg_label = item.mfg_label;
        this.long_description = item.long_description;
        this.mfg_code = item.mfg_code;
        this.renderElement();
    },

    print_label: function() {
        var self = this;
        Session.rpc('/scan_lad/print_label', {
                product_id: self.id,
                copies: self.$el.find('#copy').val()
            }).then(function(result) {
            if (result.action) {
                self.do_action(result.action);
            }
        });
    },

});

return  Item;

});


odoo.define('stock_scan_lad.MainMenu', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var Session = require('web.session');
var Item = require('stock_scan_lad.Item');

var MainMenu = Widget.extend(BarcodeHandlerMixin, {
    template: 'scan_lad_main_menu',
    events: {
        "click #search": function(){ this.on_barcode_scanned() }
    },

    init: function(parent, action) {
        this._super.apply(this, arguments);
        BarcodeHandlerMixin.init.apply(this, arguments);
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        var el_barcode = $('#barcode');
        if (barcode)
        {
            self.barcode = barcode;
             el_barcode.val(barcode);
        }
        else{
            self.barcode = el_barcode.val();
        }
        var warnings_container = $('.warnings_container');
        var not_found_warning = $('#not_found_warning');
        var too_many_warning = $('#too_many_warning');
        var items_container = $('.items_container');
        if (self.barcode) {
            Session.rpc('/scan_lad/get_products', {
                barcode: self.barcode,
            }).then(function(products) {
                not_found_warning.css('display', 'none');
                too_many_warning.css('display', 'none');
                if (products) {
                    items_container.empty();
                    _.each(products, function (item) {
                        self.item = new Item(self, item);
                        self.item.appendTo(items_container);
                    });
                    if(products.length === 1){
                        if($('#print_straightway').is(":checked")){
                            self.item.print_label();
                        }
                    }
                } else {
                    $('.barcode').text(self.barcode);
                    warnings_container.css('display', 'block');
                    not_found_warning.css('display', 'block');
                    items_container.empty();
                }
            });
        }
    },

});

core.action_registry.add('stock_scan_lad_main_menu', MainMenu);

return {
    MainMenu: MainMenu,
};

});
