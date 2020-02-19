odoo.define('returns_management.print_return_label', function(require) {
    "use strict";

    var form_widgets = require('web.form_widgets');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var framework = require('web.framework');
    var Dialog = require('web.Dialog');
    var Model = require('web.DataModel');
    var QWeb = core.qweb;

    var _t = core._t;

    var return_id = null;

    form_widgets.WidgetButton.include({
        on_click: function() {
            this._super();
            if (this.view.model == 'sale.return' && this.string == 'Print Label') {
                return_id = this.view.datarecord.id;
                print_return_label();
            }
        },
    });

    var qzVersion = 0;
    function print_return_label() {
        qz.security.setCertificatePromise(function(resolve, reject) {
            $.ajax("/lable_zabra_printer/static/src/lib/digital-certificate.txt?foo").then(resolve, reject);
        });
        var privateKey = "-----BEGIN PRIVATE KEY-----\n" +
            "MIIEugIBADANBgkqhkiG9w0BAQEFAASCBKQwggSgAgEAAoIBAQC1IMB96qLHgBY3\n" +
            "gDZasYE0QhkJvTv38x9GFtQs1FplgMU7bR3TQ0laNrBosS/XDP22qEZ2JlAoOhe8\n" +
            "ak02qGORVuQQcXhLoTFr2K+WkIs9xTR0OtMvDonGQdC6q//kHwSB+Er2FeoSgdlA\n" +
            "rrgySyneX++aocb2WKiPt5T/PIbJHR6uR8RtE0y0iahRs269LCQ/rtlAfAyGTtmr\n" +
            "A1IaMDXQ5WfDvxY3SBK9/Td/oKHr4vCtFtbrrJKTdZs05wVRxYVSm1PWOAtbZdpZ\n" +
            "AUnkNxiZQVjCNrwhXg6XqOiGhuVy69AZBRHKCQ4bDAq/aMzxo7Auob9SlPncjse5\n" +
            "5vP+M+sBAgMBAAECggEAD5Zp+mwe5hxXzR7zjoqIG/80OGpYptX9cwKz78e2n9Wd\n" +
            "I6gYUP4Rafoa5GebPl6X1whUSAa0D0IwmL5tNq73IqLfraqWN6v/nNBhDAwUb5Rx\n" +
            "Fy+YzQvrP2yakfYLZ45jzOuZR+RK6JzUHYTrxShCyihnbl9NyBWJLBUYdX63+sap\n" +
            "sI6evmjb6NPlMUN5PUqWOJItlflePGGg5IVpAMhZ0Wg0udMxmN6VHISGhn6EMEUB\n" +
            "0N4QeLX/IjeGMWUM+F2TyynOaUUOf9j/mB2d0OsaI3bKtDWF/AvoYM+7rxtKlWFr\n" +
            "MW+WGbng6nmeHspe5CFU2J8Oknd5R2YpAfm+ntmQIQKBgQDeHTMNaoYfPQtjblc6\n" +
            "39XX1ibsAqxTLLfs4dyIZZqaoeR+5E8CrjgDLIksYg00udIZ+3CIe57uRwWNmChN\n" +
            "9C8yCUsRDq/Ccra1YFhJz9nFVJzx7QbyEUHyhtdA2FFWNDli91UqQTo/XqEwELYN\n" +
            "AaHWow3HMCbbqQMwCgs/mNCybwKBgQDQwtB63eTykI6zCuj60egdEC9osg63Rfy4\n" +
            "8YjxXhmp/ePx289r88/hT6d36iWkceu0qDbEgeptGDWSeQMOobz9jmpVhaZvLVY0\n" +
            "iPIU2At8ALJIjrsgxwljv9aI3jAJORGJsERxGPe4Y1Z+EXHbPVeAffcjRtS2CXLh\n" +
            "weOqkJcxjwJ/df8NIBN3LSFA65GyxZQkBoW+J6ND6OvYyf8zKULQ31UiDkc7sjDb\n" +
            "kNQYC3wLh/cvpp3tKpSB2hPg31f2EXOnnu1Q877ZoHNQnQqR3KSPDEXnGp7REcgZ\n" +
            "QL5hnBFPJHyZ//llRQ1h5EhhWSeHj2FOmLgGmcr62bbv+pVbZG3KcQKBgDD89lVO\n" +
            "ytINEB99uOxa46AmUym7Vu61ErgHnf4d+eHFPX9c+JC5lxelTIQ8QvcS8J/lNWzp\n" +
            "m6xcGP41PX1qgOHzUIqfIU5HkkojtMMla5R+yVdzfwATFOX+d4aItTcE2FO6NGVh\n" +
            "2YfAb+SHjXNIMsdpR9xUW8gX8Yh+qkE1SvWLAoGAAotvi7mDQIURSdPFyDhk4jwc\n" +
            "3SVANyeZhnmA5fCVNaN9umqn+7aQUxtUWZkcG62Q/snMSE5wIr1GY3vvALu4kR4S\n" +
            "UUrTCs7A4WyOu5ya/FA0UMAnM4je1OSYn1tJ4fefq5WRrB2yaO2y3zz8jfpalhN1\n" +
            "W3Gx1N9sPiRn7r83148=\n" +
            "-----END PRIVATE KEY-----\n";

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
                qz.api.getVersion().then(function(data) {
                    qzVersion = data;
                });
                findPrinters();
                new Model('res.company').call('read', [1]).done(function(company) {
                    qz.printers.find(company[0].product_printer).then(function(data) {
                         return_label_set_printer(data);
                     }).catch(function(err) {
                     console.log("Found Printer Error:", err);
                    });
                });
            });
        } else {
            console.log('An active connection with QZ already exists.', 'alert-warning');
        }
    }

    function return_label_set_printer(printer) {
        var cf = return_label_set_printer();
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
            return_label_print_zpl();
        }
    }
    /// QZ Config ///
    var cfg = null;

    function return_label_get_updated_config() {
        if (cfg == null) {
            cfg = qz.configs.create(null);
        }
        return cfg;
    }

    function return_label_print_zpl() {
        ajax.jsonRpc("/qz/return_label", 'call', {'return_id': return_id}).then(function(data) {
            var config = return_label_get_updated_config();
            console.log(data);
            for (var i = 0; i < data.length; i++) {
                config.reconfigure({
                    copies: data[i].copies,
                });
                var print_data = [
                    '^XA',
                    '^CF0,40',
                    '^FO20,25^FD'+data[i].name+'^FS',
                    '^BY2,20,50',
                    '^FO20,75^BC^FD'+data[i].barcode+'^FS',
                    '^FO20,250^FD'+data[i].partslink+'^FS',
                    '^BY2,20,50',
                    '^FO20,300^BC^FD'+data[i].part_number+'^FS',
                    '^FO500,300^FD'+data[i].return_reference+'^FS',
                    '^XZ',
                ];
                console.log(print_data);
                qz.print(config, print_data).catch(function(e) { console.error(e); });
            }
        });
    }

});
