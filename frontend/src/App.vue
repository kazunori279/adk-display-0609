<template>
  <div class="relative flex size-full min-h-screen flex-col bg-white group/design-root overflow-x-hidden font-sans">
    <div class="layout-container flex h-full grow flex-col">
      <AppHeader />
      
      <div class="gap-1 px-6 flex flex-1 justify-center py-5">
        <ChatSidebar 
          @send-message="handleSendMessage" 
          @start-audio="handleStartAudio"
          @stop-audio="handleStopAudio"
          :messages="messages"
          :is-connected="isConnected"
          :is-audio-enabled="isAudioEnabled"
        />
        <MainContent 
          @select-item="handleSelectItem" 
          :current-document="currentDocument"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
import ChatSidebar from './components/ChatSidebar.vue'
import MainContent from './components/MainContent.vue'
import { useADKStreaming } from './composables/useADKStreaming.js'

const { sendTextMessage, startAudio, stopAudio, isAudioEnabled, isConnected, messages, currentDocument } = useADKStreaming()

const handleSendMessage = (message) => {
  sendTextMessage(message)
}

const handleStartAudio = () => {
  startAudio()
}

const handleStopAudio = () => {
  stopAudio()
}

const handleSelectItem = (item) => {
  console.log('Item selected:', item)
  // Here you would handle content item selection
}
</script>