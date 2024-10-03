//sample terminal client to test the SDK
//Warning! this requires SoX to work.
"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var WebSocket = __importStar(require("ws"));
var record = require("node-record-lpcm16");
var readline = require("readline");
readline.emitKeypressEvents(process.stdin);
if (process.stdin.isTTY) {
    process.stdin.setRawMode(true);
}
var common = __importStar(require("oci-common"));
var oci_aispeech_realtime_1 = require("oci-aispeech-realtime");
var model_1 = require("oci-aispeech/lib/model");
var para = "";
var serviceRegion = "us-ashburn-1";
var compartmentId = "ocid1.compartment.oc1..aaaaaaaa4bz2p36xc2wvhqvxr65s22xmp5jmm5gtlnauu3aajpx6pfgtwrxq";
var realtimeClientParameters = {
    customizations: [],
    languageCode: oci_aispeech_realtime_1.RealtimeParameters.LanguageCode.EnUs,
    modelDomain: oci_aispeech_realtime_1.RealtimeParameters.ModelDomain.Generic,
    partialSilenceThresholdInMs: 300,
    finalSilenceThresholdInMs: 2000,
    shouldIgnoreInvalidCustomizations: false,
    encoding: "audio/raw;rate=16000", //try setting to "audio/raw;rate=8000"
};
var provider = new common.ConfigFileAuthenticationDetailsProvider();
// const provider: common.SessionAuthDetailProvider = new common.SessionAuthDetailProvider();
// can be customized to include a custom OCI Config Path and Profile)
// const provider: common.SessionAuthDetailProvider = new common.SessionAuthDetailProvider("~/.oci/config", "US-PHOENIX-1");
var logs = true;
var audioStream;
var recorder;
var printLogs = function (logString) {
    if (logs)
        console.log.apply(console, __spreadArray([new Date().toISOString()], logString, false));
};
var callBack = function (eventType, event) { return __awaiter(void 0, void 0, void 0, function () {
    var closeMessage, messageEvent, data, len, error;
    return __generator(this, function (_a) {
        if (eventType === oci_aispeech_realtime_1.RealtimeWebSocketEventType.CLOSE) {
            closeMessage = event;
            try {
                recorder.stop();
            }
            catch (error) {
                printLogs(["Audio Error: " + error]);
            }
            printLogs(["WebSocket Server Closed with code: " + closeMessage.code + " " + closeMessage.reason]);
        }
        else if (eventType === oci_aispeech_realtime_1.RealtimeWebSocketEventType.OPEN) {
            printLogs(["WebSocket Client Connected"]);
            console.log("🟢");
            recorder = record.record({
                sampleRate: 16000,
                channels: 1,
            });
            audioStream = recorder.stream();
            audioStream.on("data", function (d) {
                if (realtimeSDK.realtimeWebSocketClient.readyState === realtimeSDK.realtimeWebSocketClient.OPEN)
                    realtimeSDK.realtimeWebSocketClient.send(d);
            });
        }
        else if (eventType === oci_aispeech_realtime_1.RealtimeWebSocketEventType.MESSAGE) {
            messageEvent = event;
            if (messageEvent.data) {
                printLogs([messageEvent.data]);
                data = JSON.parse(messageEvent.data.toString());
                if (data.event === model_1.RealtimeMessageConnect.event) {
                    if (!logs) {
                        process.stdout.write("\x1b[36mSession ID: " + data.sessionId + "\x1b[0m");
                    }
                    else
                        console.log("\x1b[36mSession ID: " + data.sessionId + "\x1b[0m");
                }
                else if (data.event === model_1.RealtimeMessageResult.event && !data.transcriptions[0].isFinal) {
                    len = para.split(/\r\n|\r|\n/).length;
                    if (!logs) {
                        console.clear();
                        process.stdout.write("\r" + para + "\x1b[36m" + (para.length > 0 ? " " : "") + data.transcriptions[0].transcription + "\x1b[0m" + "\n[🟠 \x1b[36mPartial\x1b[0m]\n");
                    }
                    else
                        console.log("\x1b[36mPartial: " + data.transcriptions[0].transcription + "\x1b[0m");
                }
                else if (data.event === model_1.RealtimeMessageResult.event && data.transcriptions[0].isFinal) {
                    para = para + (para.length > 0 ? " " : "") + data.transcriptions[0].transcription;
                    if (!logs) {
                        console.clear();
                        process.stdout.write("\r" + para + "\n[🟢 \x1b[32mFinal\x1b[0m]\n");
                    }
                    else
                        console.log("\x1b[32mFinal:   " + data.transcriptions[0].transcription + "\x1b[0m");
                }
            }
        }
        else if (eventType === oci_aispeech_realtime_1.RealtimeWebSocketEventType.ERROR) {
            error = event;
            try {
                audioStream.destroy();
            }
            catch (err) {
                printLogs([err]);
            }
            printLogs(["WebSocket Server Error", error.message]);
        }
        return [2 /*return*/];
    });
}); };
var startSession = function (logsEnabled) {
    if ((realtimeSDK && realtimeSDK.getWebSocketState() === oci_aispeech_realtime_1.RealtimeWebSocketState.STOPPED) || !realtimeSDK) {
        logs = logsEnabled;
        para = "";
        realtimeSDK = new oci_aispeech_realtime_1.RealtimeClient(callBack, provider, provider.getRegion(), compartmentId, "wss://realtime.aiservice-preprod.".concat(serviceRegion, ".oci.oraclecloud.com"), realtimeClientParameters);
        realtimeSDK.connect();
    }
};
var realtimeSDK;
var instructions = function () {
    console.log("Press 'e' to quit\nPress 'r' to start without logs\nPress 'l' to start with logs\nPress 's' to stop");
};
instructions();
process.stdin.on("keypress", function (str, key) {
    if (!key.ctrl && key.name === "e") {
        process.exit();
    }
    else if (!key.ctrl && key.name === "r") {
        startSession(false);
    }
    else if (!key.ctrl && key.name === "l") {
        startSession(true);
    }
    else if (!key.ctrl && key.name === "s") {
        try {
            if (realtimeSDK && realtimeSDK.getWebSocketState() !== oci_aispeech_realtime_1.RealtimeWebSocketState.STOPPED && realtimeSDK.realtimeWebSocketClient.readyState !== WebSocket.CLOSING) {
                realtimeSDK.close();
                console.log("🔴 Stopped");
                instructions();
            }
        }
        catch (e) {
            printLogs(["WebSocket Client Error", e.message]);
        }
    }
});
//# sourceMappingURL=index.js.map