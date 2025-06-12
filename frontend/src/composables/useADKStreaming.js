import { ref, reactive } from 'vue'
import { startAudioPlayerWorklet } from '@/utils/audioPlayer.js'
import { startAudioRecorderWorklet, stopMicrophone } from '@/utils/audioRecorder.js'
import { base64ToArray, arrayBufferToBase64 } from '@/utils/base64Utils.js'

export function useADKStreaming() {
  // Session and connection state
  const sessionId = Math.random().toString().substring(10)
  const isConnected = ref(false)
  const isAudioEnabled = ref(false)
  const messages = ref([])
  
  // Document display state
  const currentDocument = ref(null)
  
  // Audio state
  const audioState = reactive({
    playerNode: null,
    playerContext: null,
    recorderNode: null,
    recorderContext: null,
    micStream: null,
    audioBuffer: [],
    bufferTimer: null
  })

  // SSE connection
  let eventSource = null
  let currentMessageId = null
  let lastSystemMessage = null

  // Backend URLs - these should be configurable
  const baseUrl = 'http://localhost:8000' // Adjust based on your backend
  const sseUrl = `${baseUrl}/events/${sessionId}`
  const sendUrl = `${baseUrl}/send/${sessionId}`

  // Connect to SSE
  function connectSSE() {
    eventSource = new EventSource(`${sseUrl}?is_audio=${isAudioEnabled.value}`)

    eventSource.onopen = function () {
      console.log("SSE connection opened.")
      isConnected.value = true
    }

    eventSource.onmessage = function (event) {
      const messageFromServer = JSON.parse(event.data)
      console.log("[AGENT TO CLIENT]", messageFromServer)

      // Check if the turn is complete
      if (messageFromServer.turn_complete && messageFromServer.turn_complete === true) {
        currentMessageId = null
        return
      }

      // Check for interrupt message
      if (messageFromServer.interrupted && messageFromServer.interrupted === true) {
        // Stop audio playback if it's playing
        if (audioState.playerNode) {
          audioState.playerNode.port.postMessage({ command: "endOfAudio" })
        }
        return
      }

      // If it's audio, play it
      if (messageFromServer.mime_type === "audio/pcm" && audioState.playerNode) {
        audioState.playerNode.port.postMessage(base64ToArray(messageFromServer.data))
      }

      // If it's a document command, handle it
      if (messageFromServer.mime_type === "application/json") {
        handleDocumentCommand(messageFromServer.data)
        return
      }

      // If it's text, display it
      if (messageFromServer.mime_type === "text/plain") {
        // Add a new message for a new turn
        if (currentMessageId === null) {
          currentMessageId = Math.random().toString(36).substring(7)
          addMessage("agent", "", currentMessageId)
        }

        // Update the message content
        updateMessage(currentMessageId, messageFromServer.data)
      }
    }

    eventSource.onerror = function () {
      console.log("SSE connection error or closed.")
      isConnected.value = false
      eventSource.close()
      
      // Auto-reconnect after 5 seconds
      setTimeout(() => {
        console.log("Reconnecting...")
        connectSSE()
      }, 5000)
    }
  }

  // Send message to server
  async function sendMessage(message) {
    try {
      const response = await fetch(sendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(message)
      })
      
      if (!response.ok) {
        console.error('Failed to send message:', response.statusText)
      }
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  // Send text message
  function sendTextMessage(text) {
    if (text.trim()) {
      addMessage("user", text)
      sendMessage({
        mime_type: "text/plain",
        data: text,
      })
      console.log("[CLIENT TO AGENT]", text)
    }
  }

  // Message management
  function addMessage(sender, content, id = null) {
    const messageId = id || Math.random().toString(36).substring(7)
    messages.value.push({
      id: messageId,
      sender,
      content,
      timestamp: new Date()
    })
    return messageId
  }

  function addSystemMessage(content) {
    // Only add system message if it's different from the last one
    if (lastSystemMessage !== content) {
      lastSystemMessage = content
      addMessage("system", content)
    }
  }

  function updateMessage(messageId, additionalContent) {
    const message = messages.value.find(msg => msg.id === messageId)
    if (message) {
      message.content += additionalContent
    }
  }

  // Audio functionality
  async function startAudio() {
    try {
      // Start audio output
      const [playerNode, playerContext] = await startAudioPlayerWorklet()
      audioState.playerNode = playerNode
      audioState.playerContext = playerContext

      // Start audio input
      const [recorderNode, recorderContext, micStream] = await startAudioRecorderWorklet(audioRecorderHandler)
      audioState.recorderNode = recorderNode
      audioState.recorderContext = recorderContext
      audioState.micStream = micStream

      isAudioEnabled.value = true
      
      // Reconnect SSE with audio enabled
      if (eventSource) {
        eventSource.close()
        connectSSE()
      }
    } catch (error) {
      console.error('Error starting audio:', error)
      addSystemMessage("Failed to start audio: " + error.message)
    }
  }

  function stopAudio() {
    if (audioState.micStream) {
      stopMicrophone(audioState.micStream)
    }
    
    if (audioState.bufferTimer) {
      clearInterval(audioState.bufferTimer)
      audioState.bufferTimer = null
    }
    
    // Send any remaining buffered audio
    if (audioState.audioBuffer.length > 0) {
      sendBufferedAudio()
    }

    // Reset audio state
    Object.assign(audioState, {
      playerNode: null,
      playerContext: null,
      recorderNode: null,
      recorderContext: null,
      micStream: null,
      audioBuffer: [],
      bufferTimer: null
    })

    isAudioEnabled.value = false
  }

  // Audio recorder handler
  function audioRecorderHandler(pcmData) {
    // Add audio data to buffer
    audioState.audioBuffer.push(new Uint8Array(pcmData))
    
    // Start timer if not already running
    if (!audioState.bufferTimer) {
      audioState.bufferTimer = setInterval(sendBufferedAudio, 200) // 0.2 seconds
    }
  }

  // Send buffered audio data every 0.2 seconds
  function sendBufferedAudio() {
    if (audioState.audioBuffer.length === 0) {
      return
    }
    
    // Calculate total length
    let totalLength = 0
    for (const chunk of audioState.audioBuffer) {
      totalLength += chunk.length
    }
    
    // Combine all chunks into a single buffer
    const combinedBuffer = new Uint8Array(totalLength)
    let offset = 0
    for (const chunk of audioState.audioBuffer) {
      combinedBuffer.set(chunk, offset)
      offset += chunk.length
    }
    
    // Send the combined audio data
    sendMessage({
      mime_type: "audio/pcm",
      data: arrayBufferToBase64(combinedBuffer.buffer),
    })
    console.log("[CLIENT TO AGENT] sent %s bytes", combinedBuffer.byteLength)
    
    // Clear the buffer
    audioState.audioBuffer = []
  }

  // Handle document display commands
  function handleDocumentCommand(commandData) {
    console.log("[DOCUMENT COMMAND]", commandData)
    
    if (commandData.command === "show_document" && commandData.params && commandData.params.length > 0) {
      // Display the first document from the params
      const firstDoc = commandData.params[0]
      const documentToShow = {
        filename: firstDoc.filename,
        pageNumber: firstDoc.page_number || 1,
        basePath: `${baseUrl}/static/resources/`,
        // Add a unique timestamp to force reactivity update
        timestamp: Date.now()
      }
      
      currentDocument.value = documentToShow
      
      console.log("[DOCUMENT DISPLAY]", documentToShow)
    }
  }

  // Initialize connection
  connectSSE()

  return {
    // State
    isConnected,
    isAudioEnabled,
    messages,
    currentDocument,
    
    // Actions
    sendTextMessage,
    startAudio,
    stopAudio,
    
    // Utils
    addMessage,
    connectSSE
  }
}