<template>
  <div class="relative flex size-full min-h-screen flex-col bg-white group/design-root overflow-x-hidden font-sans">
    <div class="layout-container flex h-full grow flex-col">
      <AppHeader />
      
      <div class="gap-1 px-6 flex flex-1 justify-center py-5">
        <ChatSidebar @send-message="handleSendMessage" />
        <MainContent @select-item="handleSelectItem" />
      </div>
    </div>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
import ChatSidebar from './components/ChatSidebar.vue'
import MainContent from './components/MainContent.vue'

const handleSendMessage = (message) => {
  console.log('Message sent:', message)
  // Here you would integrate with the ADK backend
  // For now, just log the message
}

const handleSelectItem = (item) => {
  console.log('Item selected:', item)
  // Here you would handle content item selection
}
</script>