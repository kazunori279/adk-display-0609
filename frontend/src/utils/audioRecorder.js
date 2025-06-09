/**
 * Audio Recorder Worklet
 */

let micStream;

export async function startAudioRecorderWorklet(audioRecorderHandler) {
  try {
    // Create an AudioContext
    const audioRecorderContext = new AudioContext({ sampleRate: 16000 });
    console.log("AudioContext sample rate:", audioRecorderContext.sampleRate);

    console.log('Loading PCM recorder worklet...');

    // Load the AudioWorklet module
    const workletUrl = new URL('/pcm-recorder-processor.js', window.location.origin);
    console.log('Attempting to load recorder worklet from:', workletUrl.href);
    await audioRecorderContext.audioWorklet.addModule(workletUrl);

    console.log('PCM recorder worklet loaded successfully');

    // Request access to the microphone
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1 },
    });
    const source = audioRecorderContext.createMediaStreamSource(micStream);

    // Create an AudioWorkletNode that uses the PCMProcessor
    const audioRecorderNode = new AudioWorkletNode(
      audioRecorderContext,
      "pcm-recorder-processor"
    );

    // Connect the microphone source to the worklet.
    source.connect(audioRecorderNode);
    audioRecorderNode.port.onmessage = (event) => {
      // Convert to 16-bit PCM
      const pcmData = convertFloat32ToPCM(event.data);

      // Send the PCM data to the handler.
      audioRecorderHandler(pcmData);
    };
    return [audioRecorderNode, audioRecorderContext, micStream];
  } catch (error) {
    console.error('Error loading PCM recorder worklet:', error);
    throw error;
  }
}

/**
 * Stop the microphone.
 */
export function stopMicrophone(micStream) {
  micStream.getTracks().forEach((track) => track.stop());
  console.log("stopMicrophone(): Microphone stopped.");
}

// Convert Float32 samples to 16-bit PCM.
function convertFloat32ToPCM(inputData) {
  // Create an Int16Array of the same length.
  const pcm16 = new Int16Array(inputData.length);
  for (let i = 0; i < inputData.length; i++) {
    // Multiply by 0x7fff (32767) to scale the float value to 16-bit PCM range.
    pcm16[i] = inputData[i] * 0x7fff;
  }
  // Return the underlying ArrayBuffer.
  return pcm16.buffer;
}