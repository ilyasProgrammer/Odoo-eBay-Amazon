odoo.define('lable_zabra_printer.models', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    // qz.websocket.connect().then(function() {
    //     var cfg = qz.configs.create(null);
    //     qz.printers.find().then(function(data) {
    //         var list = '';
    //         for (var i = 0; i < data.length; i++) {
    //             list += data[i];
    //         }
    //         alert("Available printers: " + list);
    //     });
    // });
    // startConnection();
    // var qzVersion = 0;

    // function findVersion() {
    //     qz.api.getVersion().then(function(data) {
    //         qzVersion = data;
    //     });
    // }

    // function startConnection(config) {
    //     if (!qz.websocket.isActive()) {
    //         console.log('Waiting default');
    //         qz.websocket.connect(config).then(function() {
    //             console.log('Active success');
    //             findVersion();
    //             findPrinters();
    //         });
    //     } else {
    //         console.log('An active connection with QZ already exists.', 'alert-warning');
    //     }
    // }

    // function findPrinters() {
    //     // qz.printers.find("hp").then(function(data) {
    //     //     console.log("Found: " + data);
    //     //     setPrinter(data);
    //     // }).catch(function(err) {
    //     //     console.log("Found Printer Error:", err);
    //     // });
    //     qz.printers.find().then(function(data) {
    //         var list = '';
    //         for (var i = 0; i < data.length; i++) {
    //             list += data[i];
    //             setPrinter(data[i]);
    //         }
    //         console.log("Available printers: " + list);
    //     });
    // }

    // function setPrinter(printer) {
    //     var cf = getUpdatedConfig();
    //     cf.setPrinter(printer);

    //     if (typeof printer === 'object' && printer.name == undefined) {
    //         var shown;
    //         if (printer.file != undefined) {
    //             shown = "<em>FILE:</em> " + printer.file;
    //         }
    //         if (printer.host != undefined) {
    //             shown = "<em>HOST:</em> " + printer.host + ":" + printer.port;
    //         }
    //     } else {
    //         if (printer.name != undefined) {
    //             printer = printer.name;
    //         }

    //         if (printer == undefined) {
    //             printer = 'NONE';
    //         }
    //         printZPL();
    //     }
    // }
    // /// QZ Config ///
    // var cfg = null;

    // function getUpdatedConfig() {
    //     if (cfg == null) {
    //         cfg = qz.configs.create(null);
    //     }

    //     cfg.reconfigure({
    //         copies: 1,
    //     });
    //     return cfg
    // }

    // function printZPL() {
    //     console.log("zollllllllllllllllllllllllllllllllll")
    //     ajax.jsonRpc("/reportmypdf/lable_zabra_printer.report_zebra_producttemplatelabel/16", 'call', {})
    //         .then(function(res_data) {
    //             console.log("result", res_data);
    //             var config = getUpdatedConfig();
    //             var data = [{
    //                 type: 'raw',
    //                 format: 'base64',
    //                 data: res_data.pdf_data
    //             }];
    //             qz.print(config, data).catch(function(e) { console.error(e); });
    //         });
    // }
});
