"use strict";

var QWebChannelMessageTypes = {
    QtContext: 0,
    Idle: 1,
    Init: 2,
    IdleAck: 3,
    Signal: 4,
    Call: 5,
    Reply: 6,
    ConnectToSignal: 7,
    DisconnectFromSignal: 8,
    setProperty: 9,
    getProperty: 10
};

var QWebChannel = function (transport, initCallback) {
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel transport object is invalid!");
        return;
    }

    var channel = this;
    this.transport = transport;

    this.send = function (data) {
        if (typeof data !== "string") {
            data = JSON.stringify(data);
        }
        channel.transport.send(data);
    }

    this.transport.onmessage = function (message) {
        var data = message.data;
        if (typeof data === "string") {
            data = JSON.parse(data);
        }
        switch (data.type) {
            case QWebChannelMessageTypes.Signal:
                channel.handleSignal(data);
                break;
            case QWebChannelMessageTypes.Reply:
                channel.handleReply(data);
                break;
            case QWebChannelMessageTypes.Init:
                channel.handleInit(data);
                break;
            default:
                console.error("invalid message type: ", data.type);
                break;
        }
    }

    this.execCallbacks = {};
    this.execId = 0;
    this.exec = function (data, callback) {
        if (!callback) {
            channel.send(data);
            return;
        }
        var execId = channel.execId++;
        channel.execCallbacks[execId] = callback;
        data.id = execId;
        channel.send(data);
    };

    this.objects = {};

    this.handleInit = function (data) {
        for (var name in data.data) {
            var object = new QObject(name, data.data[name], channel);
        }
        if (initCallback) {
            initCallback(channel);
            initCallback = null;
        }
    }

    this.handleSignal = function (data) {
        var object = channel.objects[data.object];
        if (object) {
            object.signalEmitted(data.signal, data.args);
        } else {
            console.warn("Unhandled signal: " + data.object + "::" + data.signal);
        }
    }

    this.handleReply = function (data) {
        var callback = channel.execCallbacks[data.id];
        if (callback) {
            callback(data.data);
            delete channel.execCallbacks[data.id];
        } else {
            console.error("Unhandled reply: ", data.id);
        }
    }

    this.send({ type: QWebChannelMessageTypes.Init });
};

function QObject(name, data, webChannel) {
    this.__id__ = name;
    webChannel.objects[name] = this;

    this.__objectSignals__ = {};
    this.__callbacks__ = {};

    var object = this;

    for (var i = 0; i < data.methods.length; ++i) {
        var method = data.methods[i];
        this[method[0]] = (function (methodName) {
            return function () {
                var args = [];
                var callback;
                for (var i = 0; i < arguments.length; ++i) {
                    if (typeof arguments[i] === "function")
                        callback = arguments[i];
                    else
                        args.push(arguments[i]);
                }

                webChannel.exec({
                    type: QWebChannelMessageTypes.Call,
                    object: object.__id__,
                    method: methodName,
                    args: args
                }, callback);
            };
        })(method[0]);
    }

    for (var i = 0; i < data.signals.length; ++i) {
        var signal = data.signals[i];
        this[signal[0]] = (function (signalName) {
            return {
                connect: function (callback) {
                    if (typeof callback !== "function") {
                        console.error("Bad callback passed to connect().");
                        return;
                    }

                    object.__objectSignals__[signalName] = object.__objectSignals__[signalName] || [];
                    object.__objectSignals__[signalName].push(callback);

                    if (!object.__callbacks__[signalName]) {
                        object.__callbacks__[signalName] = [];
                        webChannel.exec({
                            type: QWebChannelMessageTypes.ConnectToSignal,
                            object: object.__id__,
                            signal: signalName
                        });
                    }
                },
                disconnect: function (callback) {
                    if (typeof callback !== "function") {
                        console.error("Bad callback passed to disconnect().");
                        return;
                    }

                    var signals = object.__objectSignals__[signalName];
                    if (signals) {
                        var index = signals.indexOf(callback);
                        if (index !== -1) {
                            signals.splice(index, 1);
                            if (signals.length === 0) {
                                delete object.__callbacks__[signalName];
                                webChannel.exec({
                                    type: QWebChannelMessageTypes.DisconnectFromSignal,
                                    object: object.__id__,
                                    signal: signalName
                                });
                            }
                        }
                    }
                }
            };
        })(signal[0]);
    }

    this.signalEmitted = function (signalName, args) {
        var callbacks = object.__objectSignals__[signalName];
        if (callbacks) {
            for (var i = 0; i < callbacks.length; ++i) {
                callbacks[i].apply(null, args);
            }
        }
    }

    for (var propertyName in data.properties) {
        (function (propName, propValue) {
            var propertyCache = propValue;
            Object.defineProperty(object, propName, {
                get: function () {
                    return propertyCache;
                },
                set: function (value) {
                    if (value === undefined) {
                        console.error("Property value can't be undefined!");
                        return;
                    }
                    if (value === propertyCache)
                        return;

                    propertyCache = value;
                    webChannel.exec({
                        type: QWebChannelMessageTypes.setProperty,
                        object: object.__id__,
                        property: propName,
                        value: value
                    });
                }
            });

        })(propertyName, data.properties[propertyName]);
    }
}

if (typeof module !== 'undefined') {
    module.exports = {
        QWebChannel: QWebChannel
    };
}
