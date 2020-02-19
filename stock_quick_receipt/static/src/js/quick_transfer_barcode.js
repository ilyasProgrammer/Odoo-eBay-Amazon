odoo.define('stock_quick_transfer.QuickTransfers', function (require) {
"use strict";

var core = require('web.core');
var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');

var _t = core._t;

var QuickTransfersBarcodeHandler = FormViewBarcodeHandler.extend({
    init: function(parent, context) {
        this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode
        return this._super.apply(this, arguments);
    },

    start: function() {
        this._super();
        this.form_view.options.disable_autofocus = 'true';
        this.m2x_field = 'transfer_line_ids';
        this.quantity_field = 'quantity';
        if (this.form_view_initial_mode) {
            this.form_view.options.initial_mode = this.form_view_initial_mode;
        }
    },

    pre_onchange_hook: function(barcode) {
        var state = this.form_view.datarecord.state;
        if (state === 'processed') {
            this.do_warn(_.str.sprintf(_t('%s'), state), _.str.sprintf(_t('This document is %s and cannot be edited.'), state));
            return $.Deferred().reject();
        }
        var record = null;
        var scanned_location_id = this.form_view.fields.scanned_location_id.get_value();
        var field = this.form_view.fields.transfer_line_ids;
        var view = field.viewmanager.active_view;
        // var scanned_code = this.form_view.fields.scanned_code.get_value();
        if (view) { // Weird, sometimes is undefined. Due to an asynchronous field re-rendering ?
            record = _.find(this._get_records(field), function(record) {
                return record.get('scanned_code') === barcode && record.get('location_id')[0] === scanned_location_id;
            });
        }
        if (record) {
            field.data_update(record.get('id'), {'quantity': record.get('quantity') + 1 }).then(function () {
                view.controller.reload_record(record);
            });
            return $.Deferred().resolve(false);
        } else {
            return $.Deferred().resolve(true);
        }
    },
});

core.form_widget_registry.add('quick_transfers_barcode_handler', QuickTransfersBarcodeHandler);

});
