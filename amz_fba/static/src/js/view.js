odoo.define('amz_fba.PrintFBALabel', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Form = require('web.form_widgets');

var _t = core._t;
var qz = window.qz;

Form.WidgetButton.include({

  on_confirmed: function() {
      var self = this;
      if (this.node.attrs.print == 'fba_label') {
         self.print_fba_label(this.view.datarecord.sku, this.view.datarecord.description, this.view.datarecord.copies);
      }
      return this._super();
  },

  print_fba_label: function(sku, description, copies) {
      console.log(sku, description, copies)
      var self = this;
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
              console.log('Active success');
              self.find_fba_printers(sku, description, copies);
          });
      } else {
          console.log('An active connection with QZ already exists.', 'alert-warning');
          self.find_fba_printers(sku, description, copies);
      }
  },

  find_fba_printers: function(sku, description, copies) {
      var self = this;
      new Model('res.company').call('read', [self.session.company_id]).done(function(company) {
          qz.printers.find(company[0].shipping_printer).then(function(data) {
               console.log("Found: " + data);
               self.set_fba_printer(data, sku, description, copies);
           }).catch(function(err) {
           console.log("Found Printer Error:", err);
          });
      });
  },

  set_fba_printer: function(printer, sku, description, copies) {
      var self = this;
      var cfg = qz.configs.create(null);
      cfg.reconfigure({
          copies: copies,
      });
      cfg.setPrinter(printer);
      var description_to_print = description.substring(0,47)
      if (description.length > 47) {
          description_to_print += '...'
      }
      var printData =
      [
        '^XA',
        '^FO30,40^BY2',
        '^BCN,80,N,N,N',
        '^FD' + sku + '^FS',
        '^FO30,160^A0N,40^FD' + sku + '^FS',
        '^FO30,200^A0N,30^FD' +  description_to_print + '^FS',
        '^FO30,230^A0N,30^FDNew^FS',
        '^XZ'
      ];
      qz.print(cfg, printData).catch(function(e) { console.error(e); });
  },
});

});
