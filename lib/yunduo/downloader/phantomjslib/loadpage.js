var page = require('webpage').create(),
    system = require('system');


var input, conf, url, testFx = null, testType = '', timeout = 30, ttid = 0,
    interval = 0, settings = {}, testUrl = null, loadStatus = '', requestUrl, requestInfo = {};
var extData = {'status': null, 'statusText': null, 'headers': null, 'loadStatus': null, 'errorCode': null, 'errorString': null};

page.viewportSize = { width: 1440, height: 900 };
page.settings.resourceTimeout = 5000;
page.settings.userAgent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36';


// if using phantomjs pure, without casperjs :
//      require(phantom.libraryPath + '/script/lib/foo.js')
// if using casperjs :
//      var scriptName = fs.absolute( require("system").args[3] );
//      var scriptDirectory = scriptName.substring(0, scriptName.lastIndexOf('/'));
//      require(scriptDirectory + '/script/lib/foo.js')



page.onResourceError = function(resourceError) {
    if (resourceError.url == page.url) {
        extData['errorCode'] = resourceError.errorCode
        extData['errorString'] = resourceError.errorString
    }
};

page.onError = function(msg, trace) {

  var msgStack = ['ERROR: ' + msg];

  if (trace && trace.length) {
    msgStack.push('TRACE:');
    trace.forEach(function(t) {
      msgStack.push(' -> ' + t.file + ': ' + t.line + (t['function'] ? ' (in function "' + t['function'] + '")' : '' ));
    });
  }
  console.log(msgStack.join('\n'));

};

page.onLoadStarted = function() {
    if (interval) {
        clearInterval(interval);
        interval = 0;
    };
};

page.onLoadFinished = function (status) {

    extData['loadStatus'] = status
    if (status !== "success") {
        writeError("load failed!!");
    } else {
        if (testFx != null) {
            waitFor();
        } else {
            writeResult();
        }
    }
}

page.onResourceRequested = function (req) {
    var url = req.url;
    // console.log('onResourceRequested', url);
    if (requestUrl == url) {
        requestInfo = {
            url: requestData['url'],
            method: requestData['method'],
            headers: requestData['headers']
        };
};

page.onResourceReceived = function (res) {
    if (res.stage === 'end') {
        var url = res.url
        if (page.url == res.url) {
            extData['status'] = res.status;
            extData['statusText'] = res.statusText;
            extData['headers'] = res.headers;
        }
    }
}

page.onNavigationRequested = function(url, type, willNavigate, isMainFrame) {
    if (isMainFrame && requestUrl !== url) {
        if (willNavigate) {
            requestUrl = url;
            requestInfo = {};
        }
    }
};


function merge(obj, def) {
    for (var prop in def) {
        if (obj[prop] === undefined)
            obj[prop] = def[prop];
    }
    return obj;
}

function waitFor() {
    // var condition = false, content, interval;
    // console.log('jsout 11 => ', testFx);
    interval = setInterval(function () {
        var rlt = false;
        // console.log('jsout=>', page.content.indexOf(testFx), page.content.length);
        if (testType == 'function') {
            rlt = page.evaluateJavaScript(testFx)
        } else {
            rlt = page.content.indexOf(testFx) > -1;
        }
        // console.log('waitFor', rlt)
        if (rlt) {
            clearInterval(interval);
            writeResult();
        };

    }, 250);
};



function writeResult(data, options) {
    options = options || {};
    if (ttid) {
        clearTimeout(ttid);
        ttid = 0;
    };


    try {

        var result = {};

        result['type'] = options['type'] || 'result';

        result['url'] = page.url;
        result['status_code'] = extData['status'];
        result['reason'] = extData['statusText'];
        result['cookies'] = page.cookies;
        result['content'] = page.content
        result['request'] = this.requestInfo;
        result['data'] = data || {};
        result['message'] = options['message'] || data['message'] || '';
    } catch(e) {
        console.log(e);
    }

    var str = JSON.stringify(result),
        len = str.length;

    system.stdout.write('>>>\n\n'+str+'\n\n<<<');
    system.stdout.flush();

    //console.log(JSON.stringify(data))
    phantom.exit(0);
}

function writeError(msg) {
    var data = {};
    if (ttid) {
        clearTimeout(ttid);
        ttid = 0;
    };

    data['error'] = msg;
    data['url'] = page.url;
    data['content'] = page.content;
    data['cookies'] = page.cookies;
    data['loadStatus'] = extData['loadStatus'];
    data['status'] = extData['status'];
    data['statusText'] = extData['statusText'];
    data['headers'] = extData['headers'];
    data['errorCode'] = extData['errorCode'];
    data['errorString'] = extData['errorString'];

    var str = JSON.stringify(result),
        len = str.length;

    system.stdout.write('>>>\n\n'+str+'\n\n<<<');
    system.stdout.flush();
    //console.log(JSON.stringify(data));
    phantom.exit(1);
}




try {

    ttid = setTimeout(function () {
        writeResult({
            status: 'ERR'
        }, {message: 'default TIMEOUT'});
        // writeError('default timeout');
    }, 900*1000);

    //len = system.stdin.readLine();
    //console.log('jsout:', len);
    //len = parseInt(len, 10);
    input = system.stdin.read()
    //console.log('jsout: ', input);
    conf = JSON.parse(input) || {};
    url = conf['url'];

    if (conf.timeout) {
        timeout = parseInt(conf['timeout'], 10);
    };

    // if (conf['proxy']) {
    //     phantom.setProxy(host, port, 'manual', '', '');
    //     void Phantom::setProxy(const QString &ip, const qint64 &port, const QString &proxyType, const QString &user, const QString &password)
    //     void setProxy(const QString &ip, const qint64 &port = 80, const QString &proxyType = "http", const QString &user = NULL, const QString &password = NULL);
    // };

    if (conf['userAgent']) {
        page.settings.userAgent = conf['userAgent'];
    }

    if (conf['method']) {
        settings['operation'] = conf['method'].toUpperCase();
    };
    if (conf['headers']) {
        settings['headers'] = conf['headers'];
    };
    if (conf['data']) {
        settings['data'] = conf['data'];
    };

    if (conf['testType']) {
        testType = conf['testType'];
    };
    if (conf['testFx']) {
        testFx = conf['testFx'];
    };


    page.resources = [];


    // console.log(JSON.stringify(settings, undefined, 4));
    //console.log('jsout: ',url);
    // if (settings['operation'] == 'POST') {
    //     page.open(server, 'post', settings['data']);
    // } else {
    //     page.open(url, settings);
    // }

    page.open(url, settings);

/*
    openUrl(url, conf, setting)
    conf => {
        operation:
        data:
        encoding:
        headers:{k: v}
    }
    setting => {
        "loadImages"
        "javascriptEnabled"
        "XSSAuditingEnabled"
        "userAgent"
        "localToRemoteUrlAccessEnabled"
        "userName"
        "password"
        "maxAuthAttempts"
        "resourceTimeout"
        "webSecurityEnabled"
        "javascriptCanOpenWindows"
        "javascriptCanCloseWindows"
    }
*/
    if (timeout > 0) {
        //console.log('jsout: timeout')
        if (ttid) {
            clearTimeout(ttid);
            ttid = 0;
        }
        ttid = setTimeout(function () {
            var rlt = false;
            if (testFx != null) {
                if (testType == 'function') {
                    rlt = page.evaluateJavaScript(testFx)
                } else {
                    rlt = page.content.indexOf(testFx) > -1;
                }
            }
            if (rlt) {
                writeResult({
                    status: 'OK'
                });
            } else {
                writeResult({
                    status: 'ERR'
                }, {message: 'TIMEOUT'});
            }
        }, timeout*1000);
    };

} catch (e) {
    writeError(e.message);
}






