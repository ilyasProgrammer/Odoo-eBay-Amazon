'use strict';
var qz_data = (function() {
    /// Authentication setup ///
    qz.security.setCertificatePromise(function(resolve, reject) {
        //Preferred method - from server
        //        $.ajax("assets/signing/digital-certificate.txt").then(resolve, reject);

        //Alternate method 1 - anonymous
        //        resolve();

        //Alternate method 2 - direct
        resolve("-----BEGIN CERTIFICATE-----\n" +
            "MIIE7DCCAtagAwIBAgIENjkzNjALBgkqhkiG9w0BAQUwgZgxCzAJBgNVBAYTAlVT\n" +
            "MQswCQYDVQQIDAJOWTEbMBkGA1UECgwSUVogSW5kdXN0cmllcywgTExDMRswGQYD\n" +
            "VQQLDBJRWiBJbmR1c3RyaWVzLCBMTEMxGTAXBgNVBAMMEHF6aW5kdXN0cmllcy5j\n" +
            "b20xJzAlBgkqhkiG9w0BCQEWGHN1cHBvcnRAcXppbmR1c3RyaWVzLmNvbTAeFw0x\n" +
            "OTA4MjIwNDAwMDBaFw0yMDA4MjMwNDAwMDBaMIG3MQswCQYDVQQGDAJVUzERMA8G\n" +
            "A1UECAwITWljaGlnYW4xFjAUBgNVBAcMDUhpZ2hsYW5kIHBhcmsxGzAZBgNVBAoM\n" +
            "Elh0cmVtZSBKZWVwZXJ6IExMQzEbMBkGA1UECwwSWHRyZW1lIEplZXBlcnogTExD\n" +
            "MRswGQYDVQQDDBJYdHJlbWUgSmVlcGVyeiBMTEMxJjAkBgkqhkiG9w0BCQEMF1h0\n" +
            "cmVtZWplZXBlcnpAZ21haWwuY29tMIIBIDALBgkqhkiG9w0BAQEDggEPADCCAQoC\n" +
            "ggEBALUgwH3qoseAFjeANlqxgTRCGQm9O/fzH0YW1CzUWmWAxTttHdNDSVo2sGix\n" +
            "L9cM/baoRnYmUCg6F7xqTTaoY5FW5BBxeEuhMWvYr5aQiz3FNHQ60y8OicZB0Lqr\n" +
            "/+QfBIH4SvYV6hKB2UCuuDJLKd5f75qhxvZYqI+3lP88hskdHq5HxG0TTLSJqFGz\n" +
            "br0sJD+u2UB8DIZO2asDUhowNdDlZ8O/FjdIEr39N3+goevi8K0W1uuskpN1mzTn\n" +
            "BVHFhVKbU9Y4C1tl2lkBSeQ3GJlBWMI2vCFeDpeo6IaG5XLr0BkFEcoJDhsMCr9o\n" +
            "zPGjsC6hv1KU+dyOx7nm8/4z6wECAwEAAaMjMCEwHwYDVR0jBBgwFoAUkKZQt4TU\n" +
            "uepf8gWEE3hF6Kl1VFwwCwYJKoZIhvcNAQEFA4ICAQA9aoFUxnG/dXXn4dZUqG+Y\n" +
            "Fc7v8N8+YFpUUBJdlBHK3Gh7EIHdH5HjeyPVKNVUn+ol3XH18snHlgWflvs2ZjIw\n" +
            "UoVzaECV2QbK+3Zb6Wv8v6P6ZHGt19LI6Q1AHKPSFPa3OwroCCgTxXbFZIX+YOH4\n" +
            "ja+pk6qbiyrNwSzsyEERNXZgSLzi/pDis/j10TfQ0aq7niDR10SwL12RELjPRMzF\n" +
            "dbhkap0y5F3TaOgu3FyAGasSkd9uOudHFJmVF6fDFyAW5o/PIquQQ6TBcmVwSdRi\n" +
            "tKRYCUPSq5xMN98zex6E1yZIKKz05GPCE6B6gthHHJrekQk6RHmcYkLR91VXlyNg\n" +
            "tUtS6n+W7+nm9DJLb+p4NVyI+s8sriA6Or92NjjELAEuAmiT01GkcwBSiuSA0/Fr\n" +
            "KRbr5a9F7xh0covTtIDEncrkR+79+qQwn/BkP47DcIc15YZSJ62+Byzu2Nddr2pF\n" +
            "vLHlCznqLehM/JmkPR4yN0kTEDr+ButrUNYye3nXANeBoiT9RCCkA7XauWxSGSbp\n" +
            "/maPQWJdkQsSMPw2zK196TFdN4LgB8uS7grMTblEfN+dpd2hH8GNozit5U5d4Dam\n" +
            "mikEbHCwG8lhlv+r8s86PvaIbNualS3AruY8JHuRtXtjVrG2EJY77cr9pH2VD1d7\n" +
            "cmCg2fgLKiK9WHkmz3hZ2A==\n" +
            "-----END CERTIFICATE-----\n" +
            "--START INTERMEDIATE CERT--\n" +
            "-----BEGIN CERTIFICATE-----\n" +
            "MIIFEjCCA/qgAwIBAgICEAAwDQYJKoZIhvcNAQELBQAwgawxCzAJBgNVBAYTAlVT\n" +
            "MQswCQYDVQQIDAJOWTESMBAGA1UEBwwJQ2FuYXN0b3RhMRswGQYDVQQKDBJRWiBJ\n" +
            "bmR1c3RyaWVzLCBMTEMxGzAZBgNVBAsMElFaIEluZHVzdHJpZXMsIExMQzEZMBcG\n" +
            "A1UEAwwQcXppbmR1c3RyaWVzLmNvbTEnMCUGCSqGSIb3DQEJARYYc3VwcG9ydEBx\n" +
            "emluZHVzdHJpZXMuY29tMB4XDTE1MDMwMjAwNTAxOFoXDTM1MDMwMjAwNTAxOFow\n" +
            "gZgxCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJOWTEbMBkGA1UECgwSUVogSW5kdXN0\n" +
            "cmllcywgTExDMRswGQYDVQQLDBJRWiBJbmR1c3RyaWVzLCBMTEMxGTAXBgNVBAMM\n" +
            "EHF6aW5kdXN0cmllcy5jb20xJzAlBgkqhkiG9w0BCQEWGHN1cHBvcnRAcXppbmR1\n" +
            "c3RyaWVzLmNvbTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBANTDgNLU\n" +
            "iohl/rQoZ2bTMHVEk1mA020LYhgfWjO0+GsLlbg5SvWVFWkv4ZgffuVRXLHrwz1H\n" +
            "YpMyo+Zh8ksJF9ssJWCwQGO5ciM6dmoryyB0VZHGY1blewdMuxieXP7Kr6XD3GRM\n" +
            "GAhEwTxjUzI3ksuRunX4IcnRXKYkg5pjs4nLEhXtIZWDLiXPUsyUAEq1U1qdL1AH\n" +
            "EtdK/L3zLATnhPB6ZiM+HzNG4aAPynSA38fpeeZ4R0tINMpFThwNgGUsxYKsP9kh\n" +
            "0gxGl8YHL6ZzC7BC8FXIB/0Wteng0+XLAVto56Pyxt7BdxtNVuVNNXgkCi9tMqVX\n" +
            "xOk3oIvODDt0UoQUZ/umUuoMuOLekYUpZVk4utCqXXlB4mVfS5/zWB6nVxFX8Io1\n" +
            "9FOiDLTwZVtBmzmeikzb6o1QLp9F2TAvlf8+DIGDOo0DpPQUtOUyLPCh5hBaDGFE\n" +
            "ZhE56qPCBiQIc4T2klWX/80C5NZnd/tJNxjyUyk7bjdDzhzT10CGRAsqxAnsjvMD\n" +
            "2KcMf3oXN4PNgyfpbfq2ipxJ1u777Gpbzyf0xoKwH9FYigmqfRH2N2pEdiYawKrX\n" +
            "6pyXzGM4cvQ5X1Yxf2x/+xdTLdVaLnZgwrdqwFYmDejGAldXlYDl3jbBHVM1v+uY\n" +
            "5ItGTjk+3vLrxmvGy5XFVG+8fF/xaVfo5TW5AgMBAAGjUDBOMB0GA1UdDgQWBBSQ\n" +
            "plC3hNS56l/yBYQTeEXoqXVUXDAfBgNVHSMEGDAWgBQDRcZNwPqOqQvagw9BpW0S\n" +
            "BkOpXjAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAJIO8SiNr9jpLQ\n" +
            "eUsFUmbueoxyI5L+P5eV92ceVOJ2tAlBA13vzF1NWlpSlrMmQcVUE/K4D01qtr0k\n" +
            "gDs6LUHvj2XXLpyEogitbBgipkQpwCTJVfC9bWYBwEotC7Y8mVjjEV7uXAT71GKT\n" +
            "x8XlB9maf+BTZGgyoulA5pTYJ++7s/xX9gzSWCa+eXGcjguBtYYXaAjjAqFGRAvu\n" +
            "pz1yrDWcA6H94HeErJKUXBakS0Jm/V33JDuVXY+aZ8EQi2kV82aZbNdXll/R6iGw\n" +
            "2ur4rDErnHsiphBgZB71C5FD4cdfSONTsYxmPmyUb5T+KLUouxZ9B0Wh28ucc1Lp\n" +
            "rbO7BnjW\n" +
            "-----END CERTIFICATE-----\n");
    });

    qz.security.setSignaturePromise(function(toSign) {
        return function(resolve, reject) {
            //Preferred method - from server
            //            $.ajax("/secure/url/for/sign-message?request=" + toSign).then(resolve, reject);

            //Alternate method - unsigned
            resolve();
        };
    });


    /// Connection ///
    function launchQZ() {
        if (!qz.websocket.isActive()) {
            window.location.assign("qz:launch");
            //Retry 5 times, pausing 1 second between each attempt
            startConnection({ retries: 5, delay: 1 });
        }
    }

    function startConnection(config) {
        if (!qz.websocket.isActive()) {
            updateState('Waiting', 'default');

            qz.websocket.connect(config).then(function() {
                updateState('Active', 'success');
                findVersion();
            }).catch(handleConnectionError);
        } else {
            displayMessage('An active connection with QZ already exists.', 'alert-warning');
        }
    }

    function endConnection() {
        if (qz.websocket.isActive()) {
            qz.websocket.disconnect().then(function() {
                updateState('Inactive', 'default');
            }).catch(handleConnectionError);
        } else {
            displayMessage('No active connection with QZ exists.', 'alert-warning');
        }
    }

    function listNetworkInfo() {
        qz.websocket.getNetworkInfo().then(function(data) {
            if (data.macAddress == null) { data.macAddress = 'UNKNOWN'; }
            if (data.ipAddress == null) { data.ipAddress = "UNKNOWN"; }

            var macFormatted = '';
            for (var i = 0; i < data.macAddress.length; i++) {
                macFormatted += data.macAddress[i];
                if (i % 2 == 1 && i < data.macAddress.length - 1) {
                    macFormatted += ":";
                }
            }

            displayMessage("<strong>IP:</strong> " + data.ipAddress + "<br/><strong>Physical Address:</strong> " + macFormatted);
        }).catch(displayError);
    }


    /// Detection ///
    function findPrinter(query, set) {
        $("#printerSearch").val(query);
        qz.printers.find(query).then(function(data) {
            displayMessage("<strong>Found:</strong> " + data);
            if (set) { setPrinter(data); }
        }).catch(displayError);
    }

    function findDefaultPrinter(set) {
        qz.printers.getDefault().then(function(data) {
            displayMessage("<strong>Found:</strong> " + data);
            if (set) { setPrinter(data); }
        }).catch(displayError);
    }

    function findPrinters() {
        qz.printers.find().then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                list += "&nbsp; " + data[i] + "<br/>";
            }

            displayMessage("<strong>Available printers:</strong><br/>" + list);
        }).catch(displayError);
    }


    /// Raw Printers ///
    function printEPL() {
        var config = getUpdatedConfig();

        var printData = [
            '\nN\n',
            'q609\n',
            'Q203,26\n',
            'B5,26,0,1A,3,7,152,B,"1234"\n',
            'A310,26,0,3,1,1,N,"SKU 00000 MFG 0000"\n',
            'A310,56,0,3,1,1,N,"QZ PRINT APPLET"\n',
            'A310,86,0,3,1,1,N,"TEST PRINT SUCCESSFUL"\n',
            'A310,116,0,3,1,1,N,"FROM SAMPLE.HTML"\n',
            'A310,146,0,3,1,1,N,"QZ.IO"\n',
            { type: 'raw', format: 'image', data: 'assets/img/image_sample_bw.png', options: { language: 'EPL', x: 150, y: 300 } },
            '\nP1,1\n'
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printZPL() {
        var config = getUpdatedConfig();

        var printData = [
            '^XA\n',
            '^FO50,50^ADN,36,20^FDPRINTED USING QZ PRINT PLUGIN ' + qzVersion + '\n',
            { type: 'raw', format: 'image', data: 'assets/img/image_sample_bw.png', options: { language: 'ZPLII' } },
            '^FS\n',
            '^XZ\n'
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printESCP() {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'raw', format: 'image', data: 'assets/img/image_sample_bw.png', options: { language: 'ESCP', dotDensity: 'single' } },
            { type: 'raw', data: '\nPrinted using qz-print plugin.\n\n\n\n\n\n' }
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printEPCL() {
        var config = getUpdatedConfig();

        var printData = [];
        $.merge(printData, convertEPCL('+RIB 4')); // Monochrome ribbon
        $.merge(printData, convertEPCL('F')); // Clear monochrome print buffer
        $.merge(printData, convertEPCL('+C 8')); // Adjust monochrome intensity
        $.merge(printData, convertEPCL('&R')); // Reset magnetic encoder
        $.merge(printData, convertEPCL('&CDEW 0 0')); // Set R/W encoder to ISO default
        $.merge(printData, convertEPCL('&CDER 0 0')); // Set R/W encoder to ISO default
        $.merge(printData, convertEPCL('&SVM 0')); // Disable magnetic encoding verifications
        $.merge(printData, convertEPCL('T 80 600 0 1 0 45 1 QZ INDUSTRIES')); // Write text buffer
        $.merge(printData, convertEPCL('&B 1 123456^INDUSTRIES/QZ^789012')); // Write mag strip buffer
        $.merge(printData, convertEPCL('&E*')); // Encode magnetic data
        $.merge(printData, convertEPCL('I 10')); // Print card (10 returns to print ready pos.)
        $.merge(printData, convertEPCL('MO')); // Move card to output hopper

        qz.print(config, printData).catch(displayError);
    }

    /**
     * EPCL helper function that appends a single line of EPCL data, taking into account
     * special EPCL NUL characters, data length, escape character and carriage return
     */
    function convertEPCL(data) {
        if (data == null || data.length == 0) {
            console.warn('Empty EPCL data, skipping');
        }

        // Data length for this command, in 2 character Hex (base 16) format
        var len = (data.length + 2).toString(16);
        if (len.length < 2) { len = '0' + len; }

        return [
            { type: 'raw', format: 'hex', data: 'x00x00x00' }, // Append 3 NULs
            { type: 'raw', format: 'hex', data: 'x' + len }, // Append our command length, in base16
            { type: 'raw', format: 'plain', data: data }, // Append our command
            { type: 'raw', format: 'plain', data: '\r' } // Append carriage return
        ];
    }

    function printBase64() {
        var config = getUpdatedConfig();

        // Send base64 encoded characters/raw commands to qz using data type 'base64'.
        // This will automatically convert provided base64 encoded text into text/ascii/bytes, etc.
        // This example is for EPL and contains an embedded image.
        // Please adapt to your printer language.

        //noinspection SpellCheckingInspection
        var printData = [{
            type: 'raw',
            format: 'base64',
            data: 'Ck4KcTYwOQpRMjAzLDI2CkI1LDI2LDAsMUEsMyw3LDE1MixCLCIxMjM0IgpBMzEwLDI2LDAsMywx' +
                'LDEsTiwiU0tVIDAwMDAwIE1GRyAwMDAwIgpBMzEwLDU2LDAsMywxLDEsTiwiUVogUFJJTlQgQVBQ' +
                'TEVUIgpBMzEwLDg2LDAsMywxLDEsTiwiVEVTVCBQUklOVCBTVUNDRVNTRlVMIgpBMzEwLDExNiww' +
                'LDMsMSwxLE4sIkZST00gU0FNUExFLkhUTUwiCkEzMTAsMTQ2LDAsMywxLDEsTiwiUVpJTkRVU1RS' +
                'SUVTLkNPTSIKR1cxNTAsMzAwLDMyLDEyOCz/////////6SSSX///////////////////////////' +
                '//////////6UlUqX////////////////////////////////////8kqkpKP/////////////////' +
                '//////////////////6JUpJSVf//////////////////////////////////9KpKVVU+////////' +
                '//////////////////////////8KSSlJJf5/////////////////////////////////9KUqpVU/' +
                '/7////////////////////////////////9KqUkokf//P///////////////////////////////' +
                '+VKUqpZP//+P///////////////////////////////ElKUlSf///9f/////////////////////' +
                '////////+ipSkqin////y/////////////////////////////+lVUpUlX/////r////////////' +
                '/////////////////qlJKUql/////+n////////////////////////////BFKVKUl//////8v//' +
                '/////////////////////////zVSlKUp///////0f//////////////////////////wiSlSUpf/' +
                '//////q///////////////////////////KqlJUpV///////+R//////////////////////////' +
                '4UlKSpSX///////9T/////////6L///////////////BKlKpSqP///////1X////////0qg/23/V' +
                'VVVVVVf//8CSlJKklf///////kv///////+pS0/JP8AAAAAAB///wFSlSSpV///////+pf//////' +
                '/pUoq+qfwAAAAAAH//+AClSqpUT///////9S///////8pJUlkr+AAAAAAA///4AFJSSSUv//////' +
                '/yl///////KVUpTUv8AAAAAAH///gBKSqlVU////////lX//////6UkqoiU/wAAAAAA///+ABKpJ' +
                'Uko////////JH//////UpIiqlJ/AAAAAAD///wACkSUpJX///////6q//////6pVVSqiv4AAAAAA' +
                'f///AAJVVIqpP///////pI//////pSVtSSq/wAAAAAD///8AAJSlVJVf///////Sp/////8Sq//U' +
                'qL/ttttoAP///wAAUpVSpJ///////+pT/////qkn//UlH/////AB////AABKUSpSX///////5Sn/' +
                '///+lJ//+pS/////4AP///8AABKUkpVP///////ylP////1Kv//+qr/////AA////4AAKVVJUl//' +
                '/////+lKf////KS///8kv////8AH////gAAKSSpJR///////9Kq////9Kv///5Kf////gAf///+A' +
                'AAUlUqov///////1JT////lS////qn////8AD////4AABKpKSqf///////Skj///+kr////JH///' +
                '/wAf////wAACkqUlK///////8pKv///ypf///9V////+AD/////AAAFKUVSj///////wqlP///JT' +
                '////yR////wAP////8AAAFKqkpv///////JSlf//9Sv////U/////AB/////4AAAVIpKRf//////' +
                '+ElV///pS////8of///4AP/////gAAASZVKr///////4qkj///Sn////0v////AA//////AAABUS' +
                'VJH///////glJn//8pP////KH///8AH/////+AAACtUlVf//////+ClRP//qV////9K////gA///' +
                '///4AAACEpJK///////8BSqf/+lX////yr///8AD//////wAAAVUqVH///////gUlU//5Rf////R' +
                'P///gAf//////gAAApKqTP//////8AVSV//pU////6qf//+AD//////+AAAAqkki//////8AEpVL' +
                '/+qP////1L///wAP//////4AAACSVVB/////+AFUpKX/9KP////Sv//+AB///////AAAAEqSgH//' +
                '//+ACkpSUv/lV////6k///4AP//////+AAAAUlSgf////gAJKRUpf/ST////1J///AA///////4A' +
                'AAAVJVB////gAtVFUpV/8lX///+Vf//4AH///////gAAABKSSD///wASSVVJSR/1Vf///8kf//gA' +
                '///////+AAAABVUof//4AElUpKqqv/SL////1L//8AD///////4AAAABJJQ//8AFVJKVKSSP+qj/' +
                '///Kv//gAf///////gAAAAKSpT/+ACkqSlKUkqf5Rf///6S//+AD///////+AAAAAKqpP/ABJKVS' +
                'klKqU/xUf///qp//wAP///////4AAAAAkko+gASVKUlVKlKX/VK///9Sf/+AB////////gAAAACp' +
                'UrgAKqVKVJKSlKf+Sl///0kf/4AP///////+AAAAABSVIAFJUlKqSUpKV/0pX//8qr//AA//////' +
                '//8AAAAACklACSopKSVUqVKX/qpH//okv/4AH////////gAAAAAVVKBUpUqUkkpKSk//SSv/xVK/' +
                '/AAAAAAD////AAAAAAJKWSUpVKVVUqVSp/+qqH9SlR/8AAAAAAH///4AAAAABSUklJSSlJJKUkpf' +
                '/8klQFSo//gAAAAAA////wAAAAABVKqlUkqlSqkqqU//6pUqkkof8AAAAAAB/r//AAAAAAElEpSK' +
                'qSlSSpJKL//pUqpVKr/wAAAAAAP8v/8AAAAAAJLKUqkkpSqkqSVf//yUkpKSv+AAAAAAAfqf/wAA' +
                'AAAAVClKVVUoklUqqp///UpKVVS/wAAAAAAD+S//AAAAAAAlpSkkkpVKkpKSX///JVKTpR+AAAAA' +
                'AAH9X/8AAAAAABRUpVJUqqSpSUlf///SSk/Sv4AAAAAAA/y//wAAAAAAFSVUlSUkUkpUqr////VS' +
                'v9S/AAAAAAAB/3//AAAAAAAFUkpSlJMqqUpJP////13/pT////////////8AAAAAAAEpJSlSqUkk' +
                'pVS////////Un////////////wAAAAAABJVSlSpUqpUpJX///////8q/////////////gAAAAAAC' +
                'pSqkkpKSUpSSP///////5L////////////+AAAAAAACSkVVKSklKpVV///////+SX///////////' +
                '/4AAAAAAAFSqJKlSqqiVSX///////9U/////////////gAAAAAAASpVSlSkklVJU////////yr//' +
                '//////////+AAAAAAAAkpJSklKpKSUp////////kn////////////4AAAAAAABJSqlKqkqUqVf//' +
                '/////5K/////////////gAAAAAAACpUlKpJKUqlI////////1L////////////+AAAAAAAAFSVKS' +
                'SqkpFKX////////SX////////////4AAAAAAAAiklKlSSpTKKv///////9U/////////////wAAA' +
                'AAAABSpSlSqlSiVJ////////pV/////////////AAAAAAAAVUpSkklSlUqX////////Uv///////' +
                '/////8AAAAAAAAkqUpVJJSqpVf///////8pf////////////4AAAAAAAFJKUpKqUpJUT////////' +
                '4r/////////////wAAAAAAAKqVKVKUqSSVX///////+Uv/////////////gAAAAAAASUlKSkpKql' +
                'S////////+qf/////////////AAAAAAAEkpKUlUpJJCn////////iH///////////wAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH/4B+A8AH/AAAAA' +
                'AAAAAAAAAAAAAA//AAfwD4H4HwAAf/4H4DwB//gAAAAAAAAAAAAAAAAAD/+AB/APgfgfAAB//wfw' +
                'PAf/+AAAAAAAAAAAAAgAAAAP/8AH8AfB+D4AAH//B/g8D//4AAAAAAAAAAAADwAAAA//4A/4B8H4' +
                'PgAAfB+H+DwP4HgAAAAAAAAAAAAPwAAAD4fgD/gHw/w+AAB8D4f8PB+AGAAAAAAAAAAAAA/wAAAP' +
                'g+Af/AfD/D4AAHwPh/48HwAAAAAAAAAAAAAAB/4AAA+D4B98A+P8PAAAfA+Hvjw+AAAAAAAAAAAA' +
                'AAAB/4AAD4PgH3wD4/x8AAB8H4e/PD4AAAAAAAAAAAAAAAB/8AAPh8A+PgPn/nwAAH//B5+8Pg/4' +
                'AH/j/x/4/8f+AA/8AA//wD4+A+eefAAAf/4Hj7w+D/gAf+P/H/j/x/4AA/wAD/+APj4B5554AAB/' +
                '/AeP/D4P+AB/4/8f+P/H/gAD/AAP/wB8HwH3nvgAAH/wB4f8Pw/4AH/j/x/4/8f+AA/8AA//AH//' +
                'Af+f+AAAfAAHg/wfAPgAAAAAAAAAAAAAf/AAD5+A//+B/w/4AAB8AAeD/B+A+AAAAAAAAAAAAAH/' +
                'gAAPj8D//4D/D/AAAHwAB4H8H+D4AAAAAAAAAAAAB/4AAA+H4P//gP8P8AAAfAAHgPwP//gAAAAA' +
                'AAAAAAAP8AAAD4fh+A/A/w/wAAB8AAeA/Af/+AAAAAAAAAAAAA/AAAAPg/HwB8B+B+AAAHwAB4B8' +
                'Af/4AAAAAAAAAAAADwAAAA+B+fAHwH4H4AAAfAAHgHwAf4AAAAAAAAAAAAAIAAAAD4H/8Afgfgfg' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
                'AAAAAAAAAAAAAAAAAAAAAAAAClAxLDEK'
        }];

        qz.print(config, printData).catch(displayError);
    }

    function printXML() {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'raw', format: 'xml', data: 'assets/zpl_sample.xml', options: { xmlTag: 'v7:Image' } }
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printHex() {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'raw', format: 'hex', data: '4e0d0a713630390d0a513230332c32360d0a42352c32362c' },
            { type: 'raw', format: 'hex', data: '302c31412c332c372c3135322c422c2231323334220d0a41' },
            { type: 'raw', format: 'hex', data: '3331302c32362c302c332c312c312c4e2c22534b55203030' },
            { type: 'raw', format: 'hex', data: '303030204d46472030303030220d0a413331302c35362c30' },
            { type: 'raw', format: 'hex', data: '2c332c312c312c4e2c22515a205072696e7420506c756769' },
            { type: 'raw', format: 'hex', data: '6e220d0a413331302c38362c302c332c312c312c4e2c2254' },
            { type: 'raw', format: 'hex', data: '657374207072696e74207375636365737366756c220d0a41' },
            { type: 'raw', format: 'hex', data: '3331302c3131362c302c332c312c312c4e2c2266726f6d20' },
            { type: 'raw', format: 'hex', data: '73616d706c652e68746d6c220d0a413331302c3134362c30' },
            { type: 'raw', format: 'hex', data: '2c332c312c312c4e2c227072696e7448657828292066756e' },
            { type: 'raw', format: 'hex', data: '6374696f6e2e220d0a50312c310d0a' }
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printFile(file) {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'raw', format: 'file', data: 'assets/' + file }
        ];

        qz.print(config, printData).catch(displayError);
    }


    /// Pixel Printers ///
    function printHTML() {
        var config = getUpdatedConfig();

        var colA = '<h2>*&nbsp; QZ Print Plugin HTML Printing &nbsp;*</h2>' +
            '<span style="color: #F00;">Version:</span> ' + qzVersion + '<br/>' +
            '<span style="color: #F00;">Visit:</span> https://qz.io/';
        var colB = '<img src="' + getPath() + '/assets/img/image_sample.png">';

        var printData = [{
            type: 'html',
            format: 'plain',
            data: '<html>' +
                '   <table style="font-family: monospace; border: 1px;">' +
                '       <tr style="height: 6cm;">' +
                '           <td valign="top">' + colA + '</td>' +
                '           <td valign="top">' + colB + '</td>' +
                '       </tr>' +
                '   </table>' +
                '</html>'
        }];

        qz.print(config, printData).catch(displayError);
    }

    function printPDF() {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'pdf', data: 'assets/pdf_sample.pdf' }
        ];

        qz.print(config, printData).catch(displayError);
    }

    function printImage() {
        var config = getUpdatedConfig();

        var printData = [
            { type: 'image', data: 'assets/img/image_sample.png' }
        ];

        qz.print(config, printData).catch(displayError);
    }


    /// Serial ///
    function listSerialPorts() {
        qz.serial.findPorts().then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                list += "&nbsp; <code>" + data[i] + "</code>" + serialButton(["serialPort"], [data[i]]) + "<br/>";
            }

            displayMessage("<strong>Available serial ports:</strong><br/>" + list);
        }).catch(displayError);
    }

    function openSerialPort() {
        var widthVal = $("#serialWidth").val();
        if (!widthVal) { widthVal = null; }

        var bounds = {
            begin: $("#serialBegin").val(),
            end: $("#serialEnd").val(),
            width: widthVal
        };

        qz.serial.openPort($("#serialPort").val(), bounds).then(function() {
            displayMessage("Serial port opened");
        }).catch(displayError);
    }

    function sendSerialData() {
        var properties = {
            baudRate: $("#serialBaud").val(),
            dataBits: $("#serialData").val(),
            stopBits: $("#serialStop").val(),
            parity: $("#serialParity").val(),
            flowControl: $("#serialFlow").val()
        };

        qz.serial.sendData($("#serialPort").val(), $("#serialCmd").val(), properties).catch(displayError);
    }

    function closeSerialPort() {
        qz.serial.closePort($("#serialPort").val()).then(function() {
            displayMessage("Serial port closed");
        }).catch(displayError);
    }


    /// USB ///
    function listUsbDevices() {
        qz.usb.listDevices(true).then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                var device = data[i];
                if (device.hub) { list += "USB Hub"; }

                list += "<p>" +
                    "   VendorID: <code>0x" + device.vendorId + "</code>" +
                    usbButton(["usbVendor", "usbProduct"], [device.vendorId, device.productId]) + "<br/>" +
                    "   ProductID: <code>0x" + device.productId + "</code><br/>";

                if (device.manufacturer) { list += "   Manufacturer: <code>" + device.manufacturer + "</code><br/>"; }
                if (device.product) { list += "   Product: <code>" + device.product + "</code><br/>"; }

                list += "</p><hr/>";
            }

            pinMessage("<strong>Available usb devices:</strong><br/>" + list);
        }).catch(displayError);
    }

    function listUsbDeviceInterfaces() {
        qz.usb.listInterfaces($("#usbVendor").val(), $("#usbProduct").val()).then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                list += "&nbsp; <code>0x" + data[i] + "</code>" + usbButton(["usbInterface"], [data[i]]) + "<br/>";
            }

            displayMessage("<strong>Available device interfaces:</strong><br/>" + list);
        }).catch(displayError);
    }

    function listUsbInterfaceEndpoints() {
        qz.usb.listEndpoints($("#usbVendor").val(), $("#usbProduct").val(), $("#usbInterface").val()).then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                list += "&nbsp; <code>0x" + data[i] + "</code>" + usbButton(["usbEndpoint"], [data[i]]) + "<br/>";
            }

            displayMessage("<strong>Available interface endpoints:</strong><br/>" + list);
        }).catch(displayError);
    }

    function claimUsbDevice() {
        qz.usb.claimDevice($("#usbVendor").val(), $("#usbProduct").val(), $("#usbInterface").val()).then(function() {
            displayMessage("USB Device claimed");
        }).catch(displayError);
    }

    function checkUsbDevice() {
        qz.hid.isClaimed($("#usbVendor").val(), $("#usbProduct").val()).then(function(claimed) {
            displayMessage("USB Device is " + (claimed ? "" : "not ") + "claimed");
        }).catch(displayError);
    }

    function sendUsbData() {
        qz.usb.sendData($("#usbVendor").val(), $("#usbProduct").val(), $("#usbEndpoint").val(), $("#usbData").val()).catch(displayError);
    }

    function readUsbData() {
        qz.usb.readData($("#usbVendor").val(), $("#usbProduct").val(), $("#usbEndpoint").val(), $("#usbResponse").val()).then(function(data) {
            displayMessage("<strong>Response:</strong> " + (window.readingWeight ? readScaleData(data) : data) + "<br/>");
        }).catch(displayError);
    }

    function openUsbStream() {
        qz.usb.openStream($("#usbVendor").val(), $("#usbProduct").val(), $("#usbEndpoint").val(), $("#usbResponse").val(), $("#usbStream").val()).then(function() {
            pinMessage("Waiting on device", '' + $("#usbVendor").val() + $("#usbProduct").val());
        }).catch(displayError);
    }

    function closeUsbStream() {
        qz.usb.closeStream($("#usbVendor").val(), $("#usbProduct").val(), $("#usbEndpoint").val()).then(function() {
            $('#' + $("#usbVendor").val() + $("#usbProduct").val()).attr('id', '').html("Stream closed");
        }).catch(displayError);
    }

    function releaseUsbDevice() {
        qz.usb.releaseDevice($("#usbVendor").val(), $("#usbProduct").val()).then(function() {
            displayMessage("USB Device released");
        }).catch(displayError);
    }


    /// HID ///
    function listHidDevices() {
        qz.hid.listDevices().then(function(data) {
            var list = '';
            for (var i = 0; i < data.length; i++) {
                var device = data[i];

                list += "<p>" +
                    "   VendorID: <code>0x" + device.vendorId + "</code>" +
                    usbButton(["hidVendor", "hidProduct"], [device.vendorId, device.productId]) + "<br/>" +
                    "   ProductID: <code>0x" + device.productId + "</code><br/>" +
                    "   Manufacturer: <code>" + device.manufacturer + "</code><br/>" +
                    "   Product: <code>" + device.product + "</code><br/>" +
                    "</p><hr/>";
            }

            pinMessage("<strong>Available hid devices:</strong><br/>" + list);
        }).catch(displayError);
    }

    function startHidListen() {
        qz.hid.startListening().then(function() {
            displayMessage("Started listening for HID events");
        }).catch(displayError);
    }

    function stopHidListen() {
        qz.hid.stopListening().then(function() {
            displayMessage("Stopped listening for HID events");
        }).catch(displayError);
    }

    function claimHidDevice() {
        qz.hid.claimDevice($("#hidVendor").val(), $("#hidProduct").val()).then(function() {
            displayMessage("HID Device claimed");
        }).catch(displayError);
    }

    function checkHidDevice() {
        qz.hid.isClaimed($("#hidVendor").val(), $("#hidProduct").val()).then(function(claimed) {
            displayMessage("HID Device is " + (claimed ? "" : "not ") + "claimed");
        }).catch(displayError);
    }

    function sendHidData() {
        qz.hid.sendData($("#hidVendor").val(), $("#hidProduct").val(), $("#hidData").val(), $("#hidReport").val()).catch(displayError);
    }

    function readHidData() {
        qz.hid.readData($("#hidVendor").val(), $("#hidProduct").val(), $("#hidResponse").val()).then(function(data) {
            displayMessage("<strong>Response:</strong> " + (window.readingWeight ? readScaleData(data) : data) + "<br/>");
        }).catch(displayError);
    }

    function openHidStream() {
        qz.hid.openStream($("#hidVendor").val(), $("#hidProduct").val(), $("#hidResponse").val(), $("#hidStream").val()).then(function() {
            pinMessage("Waiting on device", '' + $("#hidVendor").val() + $("#hidProduct").val());
        }).catch(displayError);
    }

    function closeHidStream() {
        qz.hid.closeStream($("#hidVendor").val(), $("#hidProduct").val()).then(function() {
            $('#' + $("#hidVendor").val() + $("#hidProduct").val()).attr('id', '').html("Stream closed");
        }).catch(displayError);
    }

    function releaseHidDevice() {
        qz.hid.releaseDevice($("#hidVendor").val(), $("#hidProduct").val()).then(function() {
            displayMessage("HID Device released");
        }).catch(displayError);
    }


    /// Resets ///
    function resetRawOptions() {
        $("#rawPerSpool").val(1);
        $("#rawEncoding").val(null);
        $("#rawEndOfDoc").val(null);
        $("#rawAltPrinting").prop('checked', false);
        $("#rawCopies").val(1);
    }

    function resetPixelOptions() {
        $("#pxlColorType").val("color");
        $("#pxlCopies").val(1);
        $("#pxlDensity").val('');
        $("#pxlDuplex").prop('checked', false);
        $("#pxlInterpolation").val("");
        $("#pxlJobName").val("");
        $("#pxlOrientation").val("");
        $("#pxlPaperThickness").val(null);
        $("#pxlPrinterTray").val(null);
        $("#pxlRasterize").prop('checked', true);
        $("#pxlRotation").val(0);
        $("#pxlScale").prop('checked', true);
        $("#pxlUnitsIN").prop('checked', true);

        $("#pxlMargins").val(0).css('display', '');
        $("#pxlMarginsTop").val(0);
        $("#pxlMarginsRight").val(0);
        $("#pxlMarginsBottom").val(0);
        $("#pxlMarginsLeft").val(0);
        $("#pxlMarginsActive").prop('checked', false);
        $("#pxlMarginsGroup").css('display', 'none');

        $("#pxlSizeWidth").val('');
        $("#pxlSizeHeight").val('');
        $("#pxlSizeActive").prop('checked', false);
        $("#pxlSizeGroup").css('display', 'none');
    }

    function checkSizeActive() {
        if ($("#pxlSizeActive").prop('checked')) {
            $("#pxlSizeGroup").css('display', '');
        } else {
            $("#pxlSizeGroup").css('display', 'none');
        }
    }

    function checkMarginsActive() {
        if ($("#pxlMarginsActive").prop('checked')) {
            $("#pxlMarginsGroup").css('display', '');
            $("#pxlMargins").css('display', 'none');
        } else {
            $("#pxlMarginsGroup").css('display', 'none');
            $("#pxlMargins").css('display', '');
        }
    }

    function resetSerialOptions() {
        $("#serialPort").val('');
        $("#serialCmd").val('');
        $("#serialBegin").val("0x0002"); //String.fromCharCode(2)
        $("#serialEnd").val("0x000D"); //String.fromCharCode(13)

        $("#serialBaud").val(9600);
        $("#serialData").val(8);
        $("#serialStop").val(1);
        $("#serialParity").val('NONE');
        $("#serialFlow").val('NONE');

        // M/T PS60 - 9600, 7, 1, EVEN, NONE
    }

    function resetUsbOptions() {
        $("#usbVendor").val('');
        $("#usbProduct").val('');

        $("#usbInterface").val('');
        $("#usbEndpoint").val('');
        $("#usbData").val('');
        $("#usbResponse").val(8);
        $("#usbStream").val(10);

        // M/T PS60 - V:0x0EB8 P:0xF000, I:0x0 E:0x81
        // Dymo S100 - V:0x0922 P:0x8009, I:0x0 E:0x82
    }

    function resetHidOptions() {
        $("#hidVendor").val('');
        $("#hidProduct").val('');

        $("#hidInterface").val('');
        $("#hidEndpoint").val('');
        $("#hidData").val('');
        $("#hidReport").val('');
        $("#hidResponse").val(8);
        $("#hidStream").val(10);
    }


    /// Page load ///
    $(document).ready(function() {
        window.readingWeight = false;

        resetRawOptions();
        resetPixelOptions();
        resetSerialOptions();
        resetUsbOptions();
        resetHidOptions();

        startConnection();

        $("#printerSearch").on('keyup', function(e) {
            if (e.which == 13 || e.keyCode == 13) {
                findPrinter($('#printerSearch').val(), true);
                return false;
            }
        });

        $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
            if (window.readingWeight) {
                $("#usbWeightRadio").click();
                $("#hidWeightRadio").click();
            } else {
                $("#usbRawRadio").click();
                $("#hidRawRadio").click();
            }
        });

        $("#usbRawRadio").click(function() { window.readingWeight = false; });
        $("#usbWeightRadio").click(function() { window.readingWeight = true; });
        $("#hidRawRadio").click(function() { window.readingWeight = false; });
        $("#hidWeightRadio").click(function() { window.readingWeight = true; });

        $("[data-toggle='tooltip']").tooltip();
    });

    qz.websocket.setClosedCallbacks(function(evt) {
        updateState('Inactive', 'default');
        console.log(evt);

        if (evt.reason) {
            displayMessage("<strong>Connection closed:</strong> " + evt.reason, 'alert-warning');
        }
    });

    qz.websocket.setErrorCallbacks(handleConnectionError);

    qz.serial.setSerialCallbacks(function(streamEvent) {
        if (streamEvent.type !== 'ERROR') {
            console.log('Serial', streamEvent.portName, 'received output', streamEvent.output);
            displayMessage("Received output from serial port [" + streamEvent.portName + "]: <em>" + streamEvent.output + "</em>");
        } else {
            console.log(streamEvent.exception);
            displayMessage("Received an error from serial port [" + streamEvent.portName + "]: <em>" + streamEvent.exception + "</em>", 'alert-error');

        }
    });

    qz.usb.setUsbCallbacks(function(streamEvent) {
        var vendor = streamEvent.vendorId;
        var product = streamEvent.productId;

        if (vendor.substring(0, 2) != '0x') { vendor = '0x' + vendor; }
        if (product.substring(0, 2) != '0x') { product = '0x' + product; }
        var $pin = $('#' + vendor + product);

        if (streamEvent.type !== 'ERROR') {
            if (window.readingWeight) {
                $pin.html("<strong>Weight:</strong> " + readScaleData(streamEvent.output));
            } else {
                $pin.html("<strong>Raw data:</strong> " + streamEvent.output);
            }
        } else {
            console.log(streamEvent.exception);
            $pin.html("<strong>Error:</strong> " + streamEvent.exception);
        }
    });

    qz.hid.setHidCallbacks(function(streamEvent) {
        var vendor = streamEvent.vendorId;
        var product = streamEvent.productId;

        if (vendor.substring(0, 2) != '0x') { vendor = '0x' + vendor; }
        if (product.substring(0, 2) != '0x') { product = '0x' + product; }
        var $pin = $('#' + vendor + product);

        if (streamEvent.type === 'RECEIVE') {
            if (window.readingWeight) {
                var weight = readScaleData(streamEvent.output);
                if (weight) {
                    $pin.html("<strong>Weight:</strong> " + weight);
                }
            } else {
                $pin.html("<strong>Raw data:</strong> " + streamEvent.output);
            }
        } else if (streamEvent.type === 'ACTION') {
            displayMessage("<strong>Device status changed:</strong> " + "[v:" + vendor + " p:" + product + "] - " + streamEvent.actionType);
        } else { //ERROR type
            console.log(streamEvent.exception);
            $pin.html("<strong>Error:</strong> " + streamEvent.exception);
        }
    });

    var qzVersion = 0;

    function findVersion() {
        qz.api.getVersion().then(function(data) {
            $("#qz-version").html(data);
            qzVersion = data;
        }).catch(displayError);
    }

    $("#askFileModal").on("shown.bs.modal", function() {
        $("#askFile").focus().select();
    });
    $("#askHostModal").on("shown.bs.modal", function() {
        $("#askHost").focus().select();
    });


    /// Helpers ///
    function handleConnectionError(err) {
        updateState('Error', 'danger');

        if (err.target != undefined) {
            if (err.target.readyState >= 2) { //if CLOSING or CLOSED
                displayError("Connection to QZ Tray was closed");
            } else {
                displayError("A connection error occurred, check log for details");
                console.error(err);
            }
        } else {
            displayError(err);
        }
    }

    function displayError(err) {
        console.error(err);
        displayMessage(err, 'alert-danger');
    }

    function displayMessage(msg, css) {
        if (css == undefined) { css = 'alert-info'; }

        var timeout = setTimeout(function() { $('#' + timeout).alert('close'); }, 5000);

        var alert = $("<div/>").addClass('alert alert-dismissible fade in ' + css)
            .css('max-height', '20em').css('overflow', 'auto')
            .attr('id', timeout).attr('role', 'alert');
        alert.html("<button type='button' class='close' data-dismiss='alert'>&times;</button>" + msg);

        $("#qz-alert").append(alert);
    }

    function pinMessage(msg, id, css) {
        if (css == undefined) { css = 'alert-info'; }

        var alert = $("<div/>").addClass('alert alert-dismissible fade in ' + css)
            .css('max-height', '20em').css('overflow', 'auto').attr('role', 'alert')
            .html("<button type='button' class='close' data-dismiss='alert'>&times;</button>");

        var text = $("<div/>").html(msg);
        if (id != undefined) { text.attr('id', id); }

        alert.append(text);

        $("#qz-pin").append(alert);
    }

    function updateState(text, css) {
        $("#qz-status").html(text);
        $("#qz-connection").removeClass().addClass('panel panel-' + css);

        if (text === "Inactive" || text === "Error") {
            $("#launch").show();
        } else {
            $("#launch").hide();
        }
    }

    function getPath() {
        var path = window.location.href;
        return path.substring(0, path.lastIndexOf("/"));
    }

    function usbButton(ids, data) {
        var click = "";
        for (var i = 0; i < ids.length; i++) {
            click += "$('#" + ids[i] + "').val('0x" + data[i] + "');$('#" + ids[i] + "').fadeOut(300).fadeIn(500);";
        }
        return '<button class="btn btn-default btn-xs" onclick="' + click + '" data-dismiss="alert">Use This</button>';
    }

    function serialButton(serialPort, data) {
        var click = "";
        for (var i = 0; i < serialPort.length; i++) {
            click += "$('#" + serialPort[i] + "').val('" + data[i] + "');$('#" + serialPort[i] + "').fadeOut(300).fadeIn(500);";
        }
        return '<button class="btn btn-default btn-xs" onclick="' + click + '" data-dismiss="alert">Use This</button>';
    }

    function formatHexInput(inputId) {
        var $input = $('#' + inputId);
        var val = $input.val();

        if (val.length > 0 && val.substring(0, 2) != '0x') {
            val = '0x' + val;
        }

        $input.val(val.toLowerCase());
    }

    /** Attempts to parse scale reading from USB raw output */
    function readScaleData(data) {
        // Filter erroneous data
        if (data.length < 4 || data.slice(2, 8).join('') == "000000000000") {
            return null;
        }

        // Get status
        var status = parseInt(data[1], 16);
        switch (status) {
            case 1: // fault
            case 5: // underweight
            case 6: // overweight
            case 7: // calibrate
            case 8: // re-zero
                status = 'Error';
                break;
            case 3: // busy
                status = 'Busy';
                break;
            case 2: // stable at zero
            case 4: // stable non-zero
            default:
                status = 'Stable';
        }

        // Get precision
        var precision = parseInt(data[3], 16);
        precision = precision ^ -256; //unsigned to signed

        // xor on 0 causes issues
        if (precision == -256) { precision = 0; }

        // Get units
        var units = parseInt(data[2], 16);
        switch (units) {
            case 2:
                units = 'g';
                break;
            case 3:
                units = 'kg';
                break;
            case 11:
                units = 'oz';
                break;
            case 12:
            default:
                units = 'lbs';
        }

        // Get weight
        data.splice(0, 4);
        data.reverse();
        var weight = parseInt(data.join(''), 16);

        weight *= Math.pow(10, precision);
        weight = weight.toFixed(Math.abs(precision));

        return weight + units + ' - ' + status;
    }


    /// QZ Config ///
    var cfg = null;

    function getUpdatedConfig() {
        if (cfg == null) {
            cfg = qz.configs.create(null);
        }

        updateConfig();
        return cfg
    }

    function updateConfig() {
        var pxlSize = null;
        if ($("#pxlSizeActive").prop('checked')) {
            pxlSize = {
                width: $("#pxlSizeWidth").val(),
                height: $("#pxlSizeHeight").val()
            };
        }

        var pxlMargins = $("#pxlMargins").val();
        if ($("#pxlMarginsActive").prop('checked')) {
            pxlMargins = {
                top: $("#pxlMarginsTop").val(),
                right: $("#pxlMarginsRight").val(),
                bottom: $("#pxlMarginsBottom").val(),
                left: $("#pxlMarginsLeft").val()
            };
        }

        var copies = 1;
        var jobName = null;
        if ($("#rawTab").hasClass("active")) {
            copies = $("#rawCopies").val();
            jobName = $("#rawJobName").val();
        } else {
            copies = $("#pxlCopies").val();
            jobName = $("#pxlJobName").val();
        }

        cfg.reconfigure({
            altPrinting: $("#rawAltPrinting").prop('checked'),
            encoding: $("#rawEncoding").val(),
            endOfDoc: $("#rawEndOfDoc").val(),
            perSpool: $("#rawPerSpool").val(),

            colorType: $("#pxlColorType").val(),
            copies: copies,
            density: $("#pxlDensity").val(),
            duplex: $("#pxlDuplex").prop('checked'),
            interpolation: $("#pxlInterpolation").val(),
            jobName: jobName,
            margins: pxlMargins,
            orientation: $("#pxlOrientation").val(),
            paperThickness: $("#pxlPaperThickness").val(),
            printerTray: $("#pxlPrinterTray").val(),
            rasterize: $("#pxlRasterize").prop('checked'),
            rotation: $("#pxlRotation").val(),
            scaleContent: $("#pxlScale").prop('checked'),
            size: pxlSize,
            units: $("input[name='pxlUnits']:checked").val()
        });
    }

    function setPrintFile() {
        setPrinter({ file: $("#askFile").val() });
        $("#askFileModal").modal('hide');
    }

    function setPrintHost() {
        setPrinter({ host: $("#askHost").val(), port: $("#askPort").val() });
        $("#askHostModal").modal('hide');
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

            $("#configPrinter").html(shown);
        } else {
            if (printer.name != undefined) {
                printer = printer.name;
            }

            if (printer == undefined) {
                printer = 'NONE';
            }
            $("#configPrinter").html(printer);
        }
    }

});
