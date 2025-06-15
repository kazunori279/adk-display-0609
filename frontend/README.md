# ADK Home AI Frontend

A Vue.js frontend application for the ADK streaming AI assistant with voice and text capabilities.

## Features

- **Real-time Text Chat**: Send and receive text messages through Server-Sent Events (SSE)
- **Voice Communication**: Full-duplex audio streaming with microphone input and audio playback
- **Live Connection Status**: Visual indicators for connection and audio status
- **Responsive UI**: Modern, clean interface built with Vue 3 and Tailwind CSS

## Installation

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000/

## Architecture

### Core Components

- **App.vue**: Main application container with ADK streaming integration
- **ChatSidebar.vue**: Chat interface with messages, audio controls, and input
- **MainContent.vue**: Content display area
- **AppHeader.vue**: Application header with branding

### Audio System

- **PCM Audio Worklets**: Custom audio processors for real-time audio streaming
  - `pcm-player-processor.js`: Handles incoming audio playback
  - `pcm-recorder-processor.js`: Processes microphone input
- **Audio Utilities**: 
  - `audioPlayer.js`: Audio playback worklet integration
  - `audioRecorder.js`: Microphone recording with PCM conversion

### Streaming Integration

- **useADKStreaming.js**: Vue composable that handles:
  - SSE connection management with auto-reconnection
  - Real-time message streaming
  - Audio buffer management and transmission
  - Session management with unique IDs

### Key Features

1. **Server-Sent Events (SSE)**: Real-time bidirectional communication
2. **Audio Worklets**: Low-latency audio processing in the browser
3. **Base64 Audio Encoding**: Efficient audio data transmission
4. **Message Buffering**: Smart audio buffering for optimal streaming
5. **Connection Recovery**: Automatic reconnection on connection loss

## Configuration

The backend connection URL can be configured in `src/composables/useADKStreaming.js`:

```javascript
const baseUrl = 'http://localhost:8000' // Adjust based on your backend
```

## Usage

1. **Text Communication**: Type messages in the input field and press Enter or click Send
2. **Voice Communication**: Click "Start Audio" to enable voice input/output
3. **Connection Status**: Monitor the connection indicator in the sidebar
4. **Audio Status**: "Audio On" badge appears when voice mode is active

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```