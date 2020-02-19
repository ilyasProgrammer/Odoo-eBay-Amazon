odoo.define('website_auto.website_auto', function (require) {
    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var website = require('website.website');
    var Model = require('web.Model');
    var Session = require('web.session');
    // var _t = core._t;
    // var remoteChained = window.chained;
    // var bootstrapSwitch = window.bootstrapSwitch;
    var select_year = $('#select_year');
    var select_make = $('#select_make');
    var select_model = $('#select_model');
    var get_parts = $('#get_parts');
    var parts_rows = $('#parts_rows');
    $(document).ready(function () {
        this.years = [];
        var currentYear = new Date().getFullYear(), years = [];
        var startYear = 1928;
        while (startYear <= currentYear) {
            this.years.push(startYear++);
        }
        this.years.reverse();
        _.each(this.years, function (item) {
            var el = "<option value='" + item + "'>" + item + "</option>";
            $(el).appendTo(select_year);
        });
        select_make.remoteChained({
            parents: "#select_year",
            url: "/select/make"
        });
        select_model.remoteChained({
            // parents: "#select_year, #select_make",  #  TODO reverse limitations possible ?
            parents: "#select_make",
            url: "/select/model"
        });
    });
    select_make.change(function () {
        select_model.empty();
    });
    select_year.change(function () {
        select_make.empty();
        select_model.empty();
    });
    get_parts.click(function () {
        var self = this;
        // framework.blockUI();
        parts_rows.empty();
        $("<div class='blink'> Please wait ... </div>").appendTo(parts_rows);
        Session.rpc('/website/get_parts', {
            year: $('#select_year').val(),
            make: $('#select_make').val(),
            model: $('#select_model').val(),
            name: $('#input_name').val()
        }).then(function (parts) {
            if(parts.length > 0) {
                parts_rows.empty();
                _.each(parts, function (part) {
                    var el = "<tr><td>" + part['PartNo'] + "</td>"
                        + "<td>" + part['ProdName'] + "</td>"
                        + "<td>" + part['MFGLabel'] + "</td>"
                        + "<td>" + part['YearID'] + "</td>"
                        + "<td>" + part['Trim'] + "</td>";
                    $(el).appendTo(parts_rows);
                });
            }
            else{
                parts_rows.empty();
                $("<div> No parts </div>").appendTo(parts_rows);
            }
        });
        // framework.unblockUI();
    });
});
