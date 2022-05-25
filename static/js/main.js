'use strict';

// Get Audio Configuration
const s = document.getElementById('speechRecognize');
const channelCount = s.getAttribute("channel_count") || 1;
const sampleRate = s.getAttribute("sample_rate") || 16000;
const sampleSize = s.getAttribute("sample_size") || 16;

// Set Websocket URL
// Other than localhost, use ssl
const pathname = location.pathname
const websocketUrl = location.hostname == '127.0.0.1' ?
    'ws://' + location.host + pathname + 'ws' :
    'wss://' + location.host + pathname + 'ws';
console.log(websocketUrl)

// HTML tag const
const show_status = document.getElementById('status');
const show_result = document.getElementById('show_result');
const stop_btn = document.querySelector('#stop_btn');
const start_btn = document.querySelector('#start_btn');
const audioInputSelect = document.querySelector('select#audioSource');
const selectors = [audioInputSelect];

// Get aduio stream and send it to websocket
async function handleSuccess(stream) {
    // When start stream, stop start button
    start_btn.disabled = true;
    stop_btn.disabled = false;
    
    // Declare audio context
    const context = new AudioContext({ sampleRate: sampleRate });
    
    // Create MediaStreamAudioSourceNode
    const source = context.createMediaStreamSource(stream);
    
    // Create AudioWorkletNode
    await context.audioWorklet.addModule('static/js/recorderProcessor.js');
    const recorder = new AudioWorkletNode(context, 'recorder');
    
    // Connect MediaStreamAudioSourceNode and AudioWorkletNode
    source.connect(recorder);
    
    // Connect AudioWorkletNode and AudioDestinationNode
    recorder.connect(context.destination);
    
    // WebSocket
    let connection = new WebSocket(websocketUrl);
    
    // Send audio data
    connection.onopen = function(event) {
        show_status.textContent = "Recognizing";
    
        // Send stream to websocket
        recorder.port.onmessage = msg => {
            connection.send(msg.data.buffer);
        };
    };
    
    // Recieve speech recognition message
    connection.onmessage = function(event) {
        if(event.data){
            show_result.innerHTML += '<div>'+ event.data +'</div>';
        }
    };
    
    function stopRecognition() {
        // Close WebSocket
        if (connection !== null) {
            connection.close();
            connection = null;
        }
        // Close Audio context
        if (context.state !== 'closed') {
            context.close();
        }
        // Change status message
        show_status.textContent= "Stopped";
    }
    
    // Speech recognition stop button
    stop_btn.onclick = function () {
        stopRecognition();
        // Enable start button
        this.disabled = true;
        start_btn.disabled = false;
    };
    
    // Change audio input select
    audioInputSelect.onchange = function () {
        stopRecognition();
        // Restart
        start();
    };
        
    return navigator.mediaDevices.enumerateDevices();
};

// Get device list and show list on select button
function gotDevices(deviceInfos) {
    // Handles being called several times to update labels. Preserve values.
    const values = selectors.map(select => select.value);
    selectors.forEach(select => {
        while (select.firstChild) {
            select.removeChild(select.firstChild);
        }
    });
    for (let i = 0; i !== deviceInfos.length; ++i) {
        const deviceInfo = deviceInfos[i];
        const option = document.createElement('option');
    
        option.value = deviceInfo.deviceId;
        if (deviceInfo.kind === 'audioinput') {
            option.text = deviceInfo.label || `microphone ${audioInputSelect.length + 1}`;
            audioInputSelect.appendChild(option);
        }
    }
    selectors.forEach((select, selectorIndex) => {
        if (Array.prototype.slice.call(select.childNodes).some(n => n.value === values[selectorIndex])) {
            select.value = values[selectorIndex];
        }
    });
}

// Connect device and start speech recognition
function start() {
    const audioSource = audioInputSelect.value;
    const constraints = {
        audio: {deviceId: audioSource ? {exact: audioSource} : undefined,
        noiseSuppression: true,
        channelCount: channelCount,
        sampleRate: sampleRate,
        sampleSize: sampleSize
        },
    };
    navigator.mediaDevices.getUserMedia(constraints).then(handleSuccess).then(gotDevices);
}

// Create device list
navigator.mediaDevices.enumerateDevices().then(gotDevices);

// Start speech recognition
start();

// Speech recognition start button
start_btn.addEventListener('click' ,start);
