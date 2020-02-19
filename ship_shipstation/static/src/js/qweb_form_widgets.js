odoo.define('ship_shipstation.qweb_form_widgets', function(require) {
	"use strict";

    var form_widgets = require('web.form_widgets');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var framework = require('web.framework');
    var Dialog = require('web.Dialog');
    var Model = require('web.DataModel');
    var QWeb = core.qweb;
    var action_model = null;
    var controller_url = null;
    var company_id = null;

    var _t = core._t;

    form_widgets.WidgetButton.include({
     	execute_action: function() {
	        var self = this;
            company_id = this.session.company_id
	        var exec_action = function() {
	            if (self.node.attrs.confirm) {
	                var def = $.Deferred();
	                Dialog.confirm(self, self.node.attrs.confirm, { confirm_callback: self.on_confirmed })
	                      .on("closed", null, function() { def.resolve(); });
	                return def.promise();
	            } else {
	                return self.on_confirmed().then(function(){
		            	if (self.view.model == 'stock.picking' && self.string == 'Get Label' || self.string == 'Get New Label'){
				            action_model = 'stock.picking';
				            controller_url = 'lable_zabra_printer.report_zebra_shipmentlabel/' + self.view.datarecord.id;
				            startConnection();
                            // new Model('stock.picking').call('process_to_validate', [self.view.datarecord.id]).then(function () {
                            //     console.log("Order validated");
                            // });
			            }
		            });
	            }
	        };
	        if (!this.node.attrs.special) {
	            return this.view.recursive_save().then(exec_action);
	        } else {
	            return exec_action();
	        }
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
            qz.printers.find(company[0].shipping_printer).then(function(data) {
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
            copies: 1,
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
                        '^FO500,20^FD'+product.manufacturer+'^FS',
                        '^BY2,20,50',
                        '^FO20,75^BC^FD'+product.barcode+'^FS',
                        '^FO20,190^FD'+product.mfg_label+'^FS',
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
										var print_type = 'pdf';
										if (picking.amz_order_type === 'fbm') {
												print_type = 'image';
										}
                    var printData =
                    [
                      {
                        type: print_type,
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
