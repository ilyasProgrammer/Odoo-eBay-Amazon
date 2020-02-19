odoo.define('stock_barcode_custom.InventoryBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');

var InventoryBarcodeCustomHandler = FormViewBarcodeHandler.extend({
    init: function(parent, context) {
        this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode
        this.m2x_field = 'line_ids';
        this.quantity_field = 'product_qty';

        return this._super.apply(this, arguments);
    },

    start: function() {
        this._super();
        this.map_barcode_method['O-CMD.MAIN-MENU'] = _.bind(this.do_action, this, 'stock_barcode.stock_barcode_action_main_menu', {clear_breadcrumbs: true});
        // FIXME: start is not a reliable place to do this.
        this.form_view.options.disable_autofocus = 'true';
        if (this.form_view_initial_mode) {
            this.form_view.options.initial_mode = this.form_view_initial_mode;
        }
    },

    pre_onchange_hook: function(barcode) {
        // If there already is an inventory line for scanned product
        // at current location, just increment its product_qty.
        var self = this;
        var record = null;
        var field = this.form_view.fields.line_ids;
        var view = field.viewmanager.active_view;
        var scan_location_id = this.form_view.fields.scan_location_id.get_value();
        var location_id = this.form_view.fields.location_id.get_value();
        console.log(location_id);
        if (view) { // Weird, sometimes is undefined. Due to an asynchronous field re-rendering ?
            record = _.find(this._get_records(field), function(record) {
                if (record.get('product_barcodes').indexOf(barcode) !== -1) {
                    if (scan_location_id) {
                        return record.get('location_id')[0] === scan_location_id;
                    } else {
                        return record.get('location_id')[0] === location_id;
                    }
                } else {
                    return false;
                }
            });
        }
        if (record) {
            field.data_update(record.get('id'), {'product_qty': record.get('product_qty') + 1}).then(function () {
                view.controller.reload_record(record);
            });
            return $.Deferred().resolve(false);
        } else {
            return $.Deferred().resolve(true);
        }
    },
});

core.form_widget_registry.add('inventory_barcode_custom_handler', InventoryBarcodeCustomHandler);

});
