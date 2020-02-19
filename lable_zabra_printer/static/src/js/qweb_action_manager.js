odoo.define('lable_zabra_printer.qweb_action_manager', function(require) {
    'use strict';

    var ajax = require('web.ajax');
    var ActionManager = require('web.ActionManager');
    var core = require('web.core');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    var Model = require('web.DataModel');
    var QWeb = core.qweb;

    var _t = core._t;
    var _lt = core._lt;

    var controller_url = null;
    var wkhtmltopdf_state;
    var action_model = null;
    var company_id = null;
    var no_copy = 1;

    // Messages that will be shown to the user (if needed).
    var WKHTMLTOPDF_MESSAGES = {
        'install': _lt('Unable to find Wkhtmltopdf on this \nsystem. The report will be shown in html.<br><br><a href="http://wkhtmltopdf.org/" target="_blank">\nwkhtmltopdf.org</a>'),
        'workers': _lt('You need to start OpenERP with at least two \nworkers to print a pdf version of the reports.'),
        'upgrade': _lt('You should upgrade your version of\nWkhtmltopdf to at least 0.12.0 in order to get a correct display of headers and footers as well as\nsupport for table-breaking between pages.<br><br><a href="http://wkhtmltopdf.org/" \ntarget="_blank">wkhtmltopdf.org</a>'),
        'broken': _lt('Your installation of Wkhtmltopdf seems to be broken. The report will be shown in html.<br><br><a href="http://wkhtmltopdf.org/" target="_blank">wkhtmltopdf.org</a>')
    };

    var trigger_download = function(session, response, c, action, options) {
        session.get_file({
            url: '/report/download',
            data: { data: JSON.stringify(response) },
            complete: framework.unblockUI,
            error: c.rpc_error.bind(c),
            success: function(data) {
                if (action && options && !action.dialog) {
                    options.on_close();
                }
            },
        });
    };

    /**
     * This helper will generate an object containing the report's url (as value)
     * for every qweb-type we support (as key). It's convenient because we may want
     * to use another report's type at some point (for example, when `qweb-pdf` is
     * not available).
     */
    var make_report_url = function(action) {
        var report_urls = {
            'qweb-html': '/report/html/' + action.report_name,
            'qweb-pdf': '/report/pdf/' + action.report_name,
            'controller': action.report_file,
        };
        // We may have to build a query string with `action.data`. It's the place
        // were report's using a wizard to customize the output traditionally put
        // their options.
        if (_.isUndefined(action.data) || _.isNull(action.data) || (_.isObject(action.data) && _.isEmpty(action.data))) {
            if (action.context.active_ids) {
                var active_ids_path = '/' + action.context.active_ids.join(',');
                // Update the report's type - report's url mapping.
                report_urls = _.mapObject(report_urls, function(value, key) {
                    return value += active_ids_path;
                });
            }
        } else {
            var serialized_options_path = '?options=' + encodeURIComponent(JSON.stringify(action.data));
            serialized_options_path += '&context=' + encodeURIComponent(JSON.stringify(action.context));
            // Update the report's type - report's url mapping.
            report_urls = _.mapObject(report_urls, function(value, key) {
                return value += serialized_options_path;
            });
        }
        return report_urls;
    };


    ActionManager.include({
        ir_actions_report_xml: function(action, options) {
            var self = this;
            company_id = this.session.company_id;
            action = _.clone(action);

            var report_urls = make_report_url(action);
            if (action.report_type === 'qweb-html') {
                var client_action_options = _.extend({}, options, {
                    report_url: report_urls['qweb-html'],
                    report_name: action.report_name,
                    report_file: action.report_file,
                    data: action.data,
                    context: action.context,
                    name: action.name,
                    display_name: action.display_name,
                });
                return this.do_action('report.client_action', client_action_options);
            } else if (action.report_type === 'qweb-pdf') {
                framework.blockUI();
                // Before doing anything, we check the state of wkhtmltopdf on the server.
                (wkhtmltopdf_state = wkhtmltopdf_state || session.rpc('/report/check_wkhtmltopdf')).then(function(state) {
                    // Display a notification to the user according to wkhtmltopdf's state.
                    if (WKHTMLTOPDF_MESSAGES[state]) {
                        self.do_notify(_t('Report'), WKHTMLTOPDF_MESSAGES[state], true);
                    }

                    if (state === 'upgrade' || state === 'ok') {
                        // Trigger the download of the PDF report.
                        var response = [
                            report_urls['qweb-pdf'],
                            action.report_type,
                        ];
                        var c = crash_manager;
                        if (action.xml_id == 'lable_zabra_printer.report_product_template_label' || action.xml_id == 'lable_zabra_printer.report_shipment_label' || action.xml_id == 'stock.action_report_location_barcode') {
                            controller_url = report_urls.controller;
                            action_model = action.model;
                            if ("copies" in action.context){
                                no_copy = action.context.copies;
                            }
                            return startConnection();
                        } else {
                            return trigger_download(self.session, response, c, action, options);
                        }
                    } else {
                        // Open the report in the client action if generating the PDF is not possible.
                        var client_action_options = _.extend({}, options, {
                            report_url: report_urls['qweb-html'],
                            report_name: action.report_name,
                            report_file: action.report_file,
                            data: action.data,
                            context: action.context,
                            name: action.name,
                            display_name: action.display_name,
                        });
                        framework.unblockUI();
                        return self.do_action('report.client_action', client_action_options);
                    }
                });
            } else if (action.report_type === 'controller') {
                framework.blockUI();
                var response = [
                    report_urls.controller,
                    action.report_type,
                ];
                var c = crash_manager;
                return trigger_download(self.session, response, c, action, options);
            } else {
                return self._super(action, options);
            }
        }
    });

    var qzVersion = 0;


    function findVersion() {
        qz.api.getVersion().then(function(data) {
            qzVersion = data;
        });
    }

    function startConnection(config) {
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
            "-----END RSA PRIVATE KEY-----\n";

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
            qz.websocket.connect(config).then(function() {
                console.log('Active success');
                findVersion();
                findPrinters();
            });
        } else {
            console.log('An active connection with QZ already exists.', 'alert-warning');
        }
    }

    function findPrinters() {
            if (action_model == 'stock.picking')
            {
                new Model('res.company').call('read', [company_id]).done(function(company) {
                    qz.printers.find(company[0].shipping_printer).then(function(data) {
                         console.log("Found: " + data);
                         setPrinter(data);
                     }).catch(function(err) {
                     console.log("Found Printer Error:", err);
                    });
                });
            }
            else if (action_model == 'stock.location')
            {
                new Model('res.company').call('read', [company_id]).done(function(company) {
                    qz.printers.find(company[0].location_printer).then(function(data) {
                         console.log("Found: " + data);
                         setPrinter(data);
                     }).catch(function(err) {
                     console.log("Found Printer Error:", err);
                    });
                });
            }
            else
            {
                new Model('res.company').call('read', [company_id]).done(function(company) {
                    qz.printers.find(company[0].product_printer).then(function(data) {
                         console.log("Found: " + data);
                         setPrinter(data);
                     }).catch(function(err) {
                     console.log("Found Printer Error:", err);
                    });
                });
            }
       }

    function setPrinter(printer) {
        var cf = getUpdatedConfig();
        cf.setPrinter(printer);
        if (typeof printer === 'object' && printer.name == undefined) {
            var shown;
            if (printer.file != undefined) {
                shown = "<em>FILE:</em> " + printer.file;
            }
            if (printer.host != undefined) {
                shown = "<em>HOST:</em> " + printer.host + ":" + printer.port;
            }
        } else {
            if (printer.name != undefined) {
                printer = printer.name;
            }

            if (printer == undefined) {
                printer = 'NONE';
            }
            if (action_model == 'stock.picking') {
                printBase64();
            }
            else if (action_model == 'stock.location'){
                printLocation();
            }
            else {
                printZPL();
            }
        }
    }
    /// QZ Config ///
    var cfg = null;

    function getUpdatedConfig() {
        if (cfg == null) {
            cfg = qz.configs.create(null);
        }

        cfg.reconfigure({
            copies: no_copy,
        });
        return cfg
    }

    function printZPL() {
        ajax.jsonRpc("/reportmypdf/" + controller_url, 'call', {})
            .then(function(res_data) {
                console.log("result", res_data);
                var config = getUpdatedConfig();
                // var data = [{
                //     type: 'raw',
                //     format: 'base64',
                //     data: res_data.pdf_data
                // }];
                // qz.print(config, data).catch(function(e) { console.error(e); });

                res_data.data.forEach(function(product) {
                    var printData =
                    [
                        '^XA',
                        '^CF0,40',
                        '^FO20,25^FD'+product.name+'^FS',
                        '^BY2,20,50',
                        '^FO20,75^BC^FD'+product.barcode+'^FS',
                        '^FO20,250^FD'+product.partslink+'^FS',
                        '^BY2,20,50',
                        '^FO20,300^BC^FD'+product.partsbarcode+'^FS',
                        '^FO500,300^FD'+product.binlocation+'^FS',
                        '^XZ',
                    ];
                    qz.print(config, printData).catch(function(e) { console.error(e); });
                    });

            }).done(function() {
                location.reload();
                console.log("Printing done");
            });
    }

    function printBase64() {
        ajax.jsonRpc("/reportmypdf/" + controller_url, 'call', {})
            .then(function(res_data) {
                var config = getUpdatedConfig();
                res_data.data.forEach(function(picking) {
                    var printData =
                    [
                      {
                        type: 'pdf',
                        format: 'base64',
                        data: picking.label
                      }
                   ];
                    qz.print(config, printData).catch(function(e) { console.error(e); });
                });

            }).done(function() {
                location.reload();
                console.log("Printing done");
            });
    }
    function printLocation() {
        ajax.jsonRpc("/reportmypdf/" + controller_url, 'call', {})
            .then(function(res_data) {
                var config = getUpdatedConfig();
                res_data.data.forEach(function(location) {
                    var printData =
                    [
                      '^XA',
                        '^CF0,130',
                        '^FO60,120^FD'+location.name+'^FS',
                        '^BY2,20,120',
                        '^FO250,250^BC^FD'+location.barcode+'^FS',
                        '^XZ',
                    ];
                    qz.print(config, printData).catch(function(e) { console.error(e); });
                    });

            }).done(function() {
                location.reload();
                console.log("Printing done");
            });
    }
});
