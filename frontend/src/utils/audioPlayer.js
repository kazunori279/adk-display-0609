/**
 * Audio Player Worklet
 */

export async function startAudioPlayerWorklet() {
    try {
        // 1. Create an AudioContext
        const audioContext = new AudioContext({
            sampleRate: 24000
        });
        
        console.log('Loading PCM player worklet...');
        
        // 2. Load your custom processor code
        const workletUrl = new URL('/pcm-player-processor.js', window.location.origin);
        console.log('Attempting to load worklet from:', workletUrl.href);
        await audioContext.audioWorklet.addModule(workletUrl);
        
        console.log('PCM player worklet loaded successfully');
        
        // 3. Create an AudioWorkletNode   
        const audioPlayerNode = new AudioWorkletNode(audioContext, 'pcm-player-processor');

        // 4. Connect to the destination
        audioPlayerNode.connect(audioContext.destination);

        // The audioPlayerNode.port is how we send messages (audio data) to the processor
        return [audioPlayerNode, audioContext];
    } catch (error) {
        console.error('Error loading PCM player worklet:', error);
        throw error;
    }
}