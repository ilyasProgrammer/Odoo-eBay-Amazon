odoo.define('sale_dashboard.GraphView', function (require) {
"use strict";
var GraphView = require('web.GraphView');

GraphView.include({
    prepare_fields: function (fields) {
        var self = this;
        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (field.string !== 'Length') {
                    if (field.type === 'integer' || field.type === 'float' || field.type === 'monetary') {
                        self.measures[name] = field;
                    }
                }
            }
        });
        this.measures.__count__ = {string: "Count", type: "integer"};
    },
});


});
