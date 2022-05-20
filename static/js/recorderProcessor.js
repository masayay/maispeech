// RecorderProcessor.js
class Recorder extends AudioWorkletProcessor {
  constructor() {
    super();
  }

  process(inputs,outputs,parameters) {
    const inp = inputs[0][0]; //Mono   
    this.port.postMessage(inp);
    return true;
  }
}

registerProcessor('recorder', Recorder);