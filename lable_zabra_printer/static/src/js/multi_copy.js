odoo.define('lable_zabra_printer.multi_copy', function(require) {
	"use strict";

    var form_widgets = require('web.form_widgets');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var framework = require('web.framework');
    var Dialog = require('web.Dialog');
    var Model = require('web.DataModel');
    var FormView = require('web.FormView');
    var ListView = require('web.ListView');
    var QWeb = core.qweb;
    var action_model = null;
    var controller_url = null;
    var company_id = null;
    var no_copy = 1;

    var _t = core._t;

ListView.include({
    render_buttons: function($node) {
        var self = this;
        this._super($node);
        company_id = this.session.company_id
        this.$buttons.on('click', '.o_single_copy', function (r){
            var selected_records = self.groups.get_selection();
            if (self.dataset.model == 'product.template'){
                action_model = 'product.template';
                controller_url = 'lable_zabra_printer.report_zebra_producttemplatelabel/' + selected_records.ids;
                startConnection();
            }
        });
        this.$buttons.on('click', '.o_multiple_copy', function (r){
            var selected_records = self.groups.get_selection();
            var dialog = new Dialog(self, {
                title: _t('Enter Copy'),
                buttons: [{text: _t("Print"), classes: 'btn-primary', close: true, click: function () {
                    no_copy = dialog.$el.find('#copy').val();
                    if (self.dataset.model == 'product.template'){
                        action_model = 'product.template';
                        controller_url = 'lable_zabra_printer.report_zebra_producttemplatelabel/' + selected_records.ids;
                        startConnection();
                    }
                }}, {text: _t("Discard"), close: true}],
                $content: QWeb.render('NoOfCopyWidget', {})
            }).open();
        });
    },
});

FormView.include({
    render_buttons: function($node) {
        var self = this;
        this._super($node);
        company_id = this.session.company_id
        this.$buttons.on('click', '.o_single_copy', function (r){
            if (self.dataset.model == 'product.template'){
                action_model = 'product.template';
                controller_url = 'lable_zabra_printer.report_zebra_producttemplatelabel/' + self.datarecord.id;
                startConnection();
            }
        });
        this.$buttons.on('click', '.o_multiple_copy', function (r){
            var dialog = new Dialog(self, {
                title: _t('Enter Copy'),
                buttons: [{text: _t("Print"), classes: 'btn-primary', close: true, click: function () {
                    no_copy = dialog.$el.find('#copy').val();
                    if (self.dataset.model == 'product.template'){
                        action_model = 'product.template';
                        controller_url = 'lable_zabra_printer.report_zebra_producttemplatelabel/' + self.datarecord.id;
                        startConnection();
                    }
                }}, {text: _t("Discard"), close: true}],
                $content: QWeb.render('NoOfCopyWidget', {})
            }).open();
        });

    },
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
          "MIIEpAIBAAKCAQEAl/EYKTQt0XyLXvfqquUQOoLZVyUSOwTIu3Fz3sA1GJWj+TTo\n" +
          "MvnNem0al+11mZsZ5qybk0FS9K8QVu4aVJS/LtYgF5aWF0xBnwD9DB3Q/lsuWNjM\n" +
          "G7k7Gk+OATy70sfuO2qyEdznk+mMMuVnduLwiESh9xw/ulKHCkmyL7J7oiJk8qFy\n" +
          "dt5SZu3mPeQiPaudEk6G2VR5iklQJw5kHD4uWucxmNxikHCO9FH5pk9+F/aYzZ8C\n" +
          "lC7ZpLdQIaUxaUBJKt14qJDzB/eJzuepv/CQVda9dhhK8tf9xaL+/nI/3Griv5fb\n" +
          "4+pOlqCpH1+YVU7lL0tv619QqDZTV/J4M1i8+wIDAQABAoIBAACCJqZr39bXZAys\n" +
          "RKMJW1Dz8R9zmmi3BI2I0V51i1my9gFt9IAoOraO29Oh2KH6Ec3ykNWd9b9l4B71\n" +
          "3bkCcd/fXDK56m0Z9kButSASEMqKVmGwZOZVnmvIoDmdtNEJM4SIbwEjIboLaQ2W\n" +
          "V7MYwe6mGPL4zZHzg8vzAuTpYph9yHacpG9PzeSmOWdDjmdsRq/RwoxHiAV2ambt\n" +
          "BdAWBsQHjKsDTj5s2pIbGuQH3ihrS1jIFMwlA7fP5RmSuExPgFiuSv8f/FAr8M9n\n" +
          "4s93B1OGuHxiB1OYXaWKwGv70b2elcO8LVF3UVodWC7YMv+CAjX/ilM0cEeosjYj\n" +
          "qrwH4VUCgYEA1WCm4T32G44pFWbjlm9LBZXmvXkbcSlOBx/JaDuiNWKDTacdY9vn\n" +
          "ed3eAH/jX+aGHBIuQEMonPb8EXfvMcDtnJyFjC4FZd05gIL99fuod/lI/g6xYSv+\n" +
          "FHT1UwwtSyANJEdsTiqk1c8P0GzOPcQiFwftmXN8ejEG+VGNHzc1RhcCgYEAtkrX\n" +
          "c/ev07KrZz2cIo9iTOgYGjwNj/zNdC1jnsJip0GGsVy+paHduWsObbuFqTwsWWg4\n" +
          "gK2ODXIYBc7Kg7BrGPHNLNXpu+eZMs5sS8jGaIshi29emTnAFzVy3enAcz2s66QJ\n" +
          "nXd0MA+3P5rtwIx0Z4rT65uYvxmRiHwq7oD4sr0CgYEAls9pI2mXuIIRp37A/GJM\n" +
          "s/Xuz5v5OVHoREDDKVh8nR6zjv6+VwXl5MxbTB8XpYBY6R4wclsFKWunXPFXreKe\n" +
          "DkLSYPFl/0kMizgKJwFnYORgIrBfzj45plvDyJ6ipKZSo4GXmueo+TUQCE/etOka\n" +
          "7ww7cmmdYP+l3jE1fQqYLKECgYAUrjrxKhllb/CoHsI23YNubCpH16ZGPozkcD3M\n" +
          "BguBJBruxjHOwqVP4shZRJvuTihN4FgAqS/jcJ0vE33AIOSViOEZBA+nRKgJrod0\n" +
          "tYtk0tv0YKcfxQB44ZRtfpZZvJaAiTSaC7I/vZixe5cbcBPIp2RRZ26Vx4XOMSAB\n" +
          "vNn6FQKBgQCdCiwikWW8ThGh3n7HMZ2ps9k+cRfblyADUHhawaO1mZFYthMJ8mEY\n" +
          "5/4uwTchbM96YBQYjlx+vrB1HaZyMzqYeaSqFSX7+KkKn1Tex1Nga395dUMzMqK8\n" +
          "euHRdS2ISaiFSryI2ZFz7Ut6DSqqgt5q1X4d/9gDFWon1vfQbtBj1g==\n" +
          "-----END RSA PRIVATE KEY-----\n";

				console.log(privateKey);

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
        new Model('res.company').call('read', [company_id]).done(function(company) {
            qz.printers.find(company[0].product_printer).then(function(data) {
                 console.log("Found: " + data);
                 setPrinter(data);
             }).catch(function(err) {
             console.log("Found Printer Error:", err);
            });
        });
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
                    console.log("ddddddddddddd", printData)
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
                    console.log("ddddddddddddd", printData)
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
                console.log("result", res_data);
                var config = getUpdatedConfig();
                res_data.data.forEach(function(location) {
                    var printData =
                    [
                      '^XA',
                        '^CF0,130',
                        '^FO100,120^FD'+location.name+'^FS',
                        '^BY2,20,120',
                        '^FO250,250^BC^FD'+location.barcode+'^FS',
                        '^XZ',
                    ];
                    console.log("ddddddddddddd", printData)
                    qz.print(config, printData).catch(function(e) { console.error(e); });
                    });

            }).done(function() {
                location.reload();
                console.log("Printing done");
            });
    }
});
