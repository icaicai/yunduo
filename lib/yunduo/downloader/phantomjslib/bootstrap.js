
// Common polyfills
void function() {
    // cujos bind shim instead of MDN shim, see #1396
    var isFunction = function(o) {
      return 'function' === typeof o;
    };
    var bind;
    var slice = [].slice;
    var proto = Function.prototype;
    var featureMap = {
      'function-bind': 'bind'
    };
    function has(feature) {
      var prop = featureMap[feature];
      return isFunction(proto[prop]);
    }
    // check for missing features
    if (!has('function-bind')) {
      // adapted from Mozilla Developer Network example at
      // https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Function/bind
      bind = function bind(obj) {
        var args = slice.call(arguments, 1),
          self = this,
          nop = function() {
          },
          bound = function() {
            return self.apply(this instanceof nop ? this : (obj || {}), args.concat(slice.call(arguments)));
          };
        nop.prototype = this.prototype || {}; // Firefox cries sometimes if prototype is undefined
        bound.prototype = new nop();
        return bound;
      };
      proto.bind = bind;
    }

}();

// Custom base error
var CasperError = function CasperError(msg) {
    "use strict";
    Error.call(this);
    this.message = msg;
    this.name = 'CasperError';
};
CasperError.prototype = Object.getPrototypeOf(new Error());

// casperjs env initialization
(function(global, phantom, system){
    "use strict";
    // phantom args
    var phantomArgs = system.args.slice(1);
    phantom.casperEngine = "phantomjs";

    if (phantom.casperLoaded) {
        return;
    }

    function __exit(statusCode){
        setTimeout(function() { phantom.exit(statusCode); }, 0);
    }

    function __die(message) {
        if (message) {
            console.error(message);
        }
        __exit(1);
    }

    function __terminate(message) {
        if (message) {
            console.log(message);
        }
        __exit();
    }

    (function (version) {
        // required version check
        if (phantom.casperEngine === 'phantomjs') {
            if (version.major === 1) {
                if (version.minor < 9) {
                    return __die('CasperJS needs at least PhantomJS v1.9 or later.');
                }
                if (version.minor === 9 && version.patch < 1) {
                    return __die('CasperJS needs at least PhantomJS v1.9.1 or later.');
                }
            } else if (version.major === 2) {
                // No requirements yet known
            } else {
                return __die('CasperJS needs PhantomJS v1.9.x or v2.x');
            }
        }
    })(phantom.version);

    // Hooks in default phantomjs error handler
    phantom.onError = function onPhantomError(msg, trace) {
        phantom.defaultErrorHandler.apply(phantom, arguments);
        // print a hint when a possible casperjs command misuse is detected
        if (msg.indexOf("ReferenceError: Can't find variable: casper") === 0) {
            console.error('Hint: you may want to use the `casperjs test` command.');
        }
        // exits on syntax error
        if (msg.indexOf('SyntaxError: ') === 0) {
            __die();
        }
    };

    // Patching fs
    var fs = (function patchFs(fs) {
        if (!fs.hasOwnProperty('basename')) {
            fs.basename = function basename(path) {
                return path.replace(/.*\//, '');
            };
        }
        if (!fs.hasOwnProperty('dirname')) {
            fs.dirname = function dirname(path) {
                if (!path) return undefined;
                return path.toString().replace(/\\/g, '/').replace(/\/[^\/]*$/, '');
            };
        }
        if (!fs.hasOwnProperty('isWindows')) {
            fs.isWindows = function isWindows() {
                var testPath = arguments[0] || this.workingDirectory;
                return (/^[a-z]{1,2}:/i).test(testPath) || testPath.indexOf("\\\\") === 0;
            };
        }
        if (fs.hasOwnProperty('joinPath')) {
            fs.pathJoin = fs.joinPath;
        } else if (!fs.hasOwnProperty('pathJoin')) {
            fs.pathJoin = function pathJoin() {
                return Array.prototype.filter.call(arguments,function(elm){
                    return typeof elm !== "undefined" && elm !== null;
                }).join('/');
            };
        }

        return fs;
    })(require('fs'));

    // CasperJS root path
    if (!phantom.casperPath) {
        try {
            phantom.casperPath = phantomArgs.map(function _map(arg) {
                var match = arg.match(/^--casper-path=(.*)/);
                if (match) {
                    return fs.absolute(match[1]);
                }
            }).filter(function _filter(path) {
                return fs.isDirectory(path);
            }).pop();
        } catch (e) {
            return __die("Couldn't find nor compute phantom.casperPath, exiting.");
        }
    }

    // declare a dummy patchRequire function
    global.patchRequire = function(req) {return req;};
    require.paths.push(phantom.casperPath);
    require.paths.push(fs.workingDirectory);

    // casper loading status flag
    phantom.casperLoaded = true;

    // console.log('init environment!!', require('utils'));
    // setTimeout(function() { phantom.exit(99); }, 0);
    // try {
        var utils = require('utils'),
            input = system.stdin.read(),
            conf = JSON.parse(input) || {},
            url = conf.url,
            settings = conf.settings || {},
            options = conf.options || {},
            requestInfo = {},
            defaults = {
                verbose: true,
                exitOnError: false,
                retryTimeout: 300,      //0.1s
                waitTimeout: 60000,     //60s
                viewportSize: { width: 1440, height: 900 },
                pageSettings: {
                    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.86 Safari/537.36"
                },
                onRunComplete: function (casper) {
                    // var data = {
                    //     status: 'OK',
                    //     complete: true
                    // };
                    // if (conf.__include_content === true) {
                    //     data['content'] = this.getPageContent()
                    // }
                    // this.done(data);
                    console.log('on onRunComplete ===')
                    this.send_result('OK');
                },
                onLoadError: function (casper, url, status) {
                    // this.done({status: 'ERR'});
                    // this.return_result('error', {
                    //     status: 'ERR'
                    // });
                    var data = {
                        type: 'error',
                        data: {
                            status: status,
                            message: '页面加载失败'
                        },
                        message: '页面加载失败',
                        url: url,
                        status_code: this.currentHTTPStatus,
                        reason: this.currentResponse['statusText']
                    }
                    if (casper.currentHTTPStatus == 200) {

                    }
                    // this.exit();
                },
                onTimeout: function () {
                    this.send_result('OK', {}, {
                        message: utils.format("Script timeout of %dms reached, exiting.", this.options.timeout)
                    });

//                    var data = {
//                        type: 'error',
//                        data: {
//                            status: 'ERR',
//                            message: '脚本执行超时'
//                        },
//                        // cookies: this.page.cookies,
//                        content: this.getPageContent(),
//                        message: '脚本执行超时',
//                        url : this.requestUrl,
//                        status_code: 572,
//                        reason: utils.format("Script timeout of %dms reached, exiting.", this.options.timeout)
//                    }
//                    this.send(data);
//                    this.exit();
                    // this.send_result('timeout', {
                    //     status: 'ERR'
                    // })

                },
                onResourceRequested: function(casper, requestData, request) {
                    var url = requestData.url;
                    // console.log('onResourceRequested', url);
                    if (casper.requestUrl == url) {
                        // console.log('onResourceRequested', JSON.stringify(requestData));
                        casper.requestInfo = {
                            url: requestData['url'],
                            method: requestData['method'],
                            headers: requestData['headers']
                        };
                    }
                    for (var i=0; i<this._blocked_urls.length; i++) {
                        var rex = this._blocked_urls[i];
                        if (rex.test(url)) {
                            request.abort();
                            break;
                        }
                    }

                }
            },
            casper;
        // console.log('init environment 44', input);
        options = utils.mergeObjects(defaults, options);
        casper = window.casper = require('casper').create(options);
        window.environ = conf.environ || {};
        casper._blocked_urls = [];
        casper.requestInfo = {};
        casper.__completed = false;

        // casper.pause = function () {
        //     this.unwait();
        //     clearInterval(this.checker);
        // }

        // casper.done = function (data) {
        //     data = utils.mergeObjects(data, {
        //         'cookies': this.page.cookies,
        //         'url': this.requestUrl,
        //         'status_code': this.currentHTTPStatus,
        //         'reason': this.currentResponse['statusText']
        //     });
        //     this.send(data);
        //     setTimeout(function() { phantom.exit(0); }, 100);
        //     // this.exit();
        // }

        // casper.pageInfo = function () {
        //     casper.page.cookies;
        // }

        casper.on_complete = function () {
            console.log('on on__Complete ===')
            if (casper.__completed) {
                return ;
            }
            casper.__completed = true;

            this.send_result({
                status: 'OK'
            });
        }

        casper.add_blocked = function (rex) {
            if (utils.isString(rex)) {
                rex = new RegExp(rex);
            }
            this._blocked_urls.push(rex);
        }

        casper.send_qrcode = function (image) {
            var data = {
                qrcode: image
            }
            data['status'] = image && image.length ? 'OK' : 'ERR';

            casper.send_notify('qrcode', data)
        };

        casper.send_notify = function (type, data, options) {
//            this.send({
//                type: 'notify',
//                data: {
//                    type: type,
//                    data: data
//                }
//            })
            options = options || {};
            casper.set_result(options['status'] || 'OK', data, {exit: false, __notify__: type, __resp__: false})
        };
        casper.set_next_form = function (form, data, options) {
            options = options || {};
            options['form'] = form
            return casper.set_result('NXF', data, options)
        }

        casper.set_next_action = function (action, data, options) {
            options = options || {};
            options['form'] = form
            return casper.set_result('NXF', data, options)
        }
//            var result = {
//                type: 'next',
//                name: next,
//                data: data || {},
//                form: form || {},
//                cookies: this.page.cookies,
//                url: this.getCurrentUrl(),
//                message: message || ''
//            }
//
//            this.send(result);
//            setTimeout(function() { phantom.exit(0); }, 100);
//        }

        casper.set_result = function (status, data, options) {
            var result = {
                status: status || 'OK'
            };
            options = options || {};

            if (options['__resp__'] !== false) {
                result['resp'] = {
                    url: this.getCurrentUrl(),
                    status_code: this.currentHTTPStatus,
                    encoding: 'utf8',
                    reason: this.currentResponse['statusText'],
                    headers: this.currentResponse['headers'],
                    cookies: this.page.cookies,
                    content: this.getPageContent(),
                    request: this.requestInfo
                }
            }

            result['data'] = data || {};
            result['meta'] = window.environ;
            result['message'] = options['message'] || '';
            if (options['next'])
                result['next'] = options['next']
            if (options['form'])
                result['form'] = options['form']
            if (options['__notify__'])
                result['__notify__'] = options['__notify__']

            this.send(result);

            if (options['exit'] !== false) {
                setTimeout(function() { phantom.exit(0); }, 100);
            }
        }


        casper.send = function (data) {
            var str = JSON.stringify(data),
                len = str.length;

            system.stdout.write('>>>\n\n'+str+'\n\n<<<');
            // system.stdout.write(str);
            system.stdout.flush();
        }

        // console.log('conf.jscode', conf.jscode);
        // if (url) {
        //     // if (conf.jscode && conf.jscode.indexOf(url) == -1) {
        //         casper.start();
        //         casper.open(url, settings);
        //     // }
        // }

        if (conf.jscode) {
            var jscode = conf.jscode,
                sjs = [];
            jscode = jscode.replace(/(^\s*)|(\s*$)/g, "");
            if (/^function\s*\(/.test(jscode)) {
                //jscode = 'function () {' + jscode + ';;}';
                if (!/\s*casper\.start\(/g.test(jscode)) {
                    sjs.push(';');
                    sjs.push('casper.start();');
                    if (url) {
                        // var o = [];
                        // o.push('casper.open(');
                        // o.push('"');
                        // o.push(url.replace('"', '\\"'));
                        // o.push('", ');
                        // o.push(JSON.stringify(settings));
                        // o.push(');\n')
                        // sjs.push(o.join(''));
                        window.__url = url;
                        window.__settings = settings;
                        sjs.push('casper.open(window.__url, window.__settings);');
                    }
                }


                if (!/\s*casper\.run\(/g.test(jscode)) {
                    var i = jscode.lastIndexOf('}');
                    sjs.push(jscode.substring(0, i-1));
                    sjs.push(';');
                    sjs.push('casper.run(casper.on_complete);');
                    sjs.push(';}');
                    jscode = sjs.join('\n');
                }
            } else {
                // sjs.push(';');
                sjs.push('function () {');
                if (!/\s*casper\.start\(/g.test(jscode)) {
                    sjs.push(';');
                    sjs.push('casper.start();\n');
                    if (url) {
                        // var o = [];
                        // o.push('casper.open(');
                        // o.push('"');
                        // o.push(url.replace('"', '\\"'));
                        // o.push('", ');
                        // o.push(JSON.stringify(settings));
                        // o.push(');\n')
                        // sjs.push(o.join(''));
                        window.__url = url;
                        window.__settings = settings;
                        sjs.push('casper.open(window.__url, window.__settings);');
                    }
                }

                sjs.push(jscode);
                if (!/\s*casper\.run\(/g.test(jscode)) {
                    sjs.push(';');
                    sjs.push('casper.run(casper.on_complete);')
                }
                sjs.push(';');
                sjs.push('}');
                jscode = sjs.join('\n');
            }
            // console.log(jscode);
            phantom.page.evaluateJavaScript(jscode);
        }

    // } catch (e) {
    //     var data = {
    //         url: '',
    //         status: 555,
    //         statusText: e.stack
    //     };

    //     system.stdout.write('>>>\n\n'+JSON.stringify(data)+'\n\n<<<');
    //     system.stdout.flush();
    //     casper.exit();
    // }


})(this, phantom, require('system'));
