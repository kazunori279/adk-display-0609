<template>
  <div class="layout-content-container flex flex-col w-80">
    <!-- Connection Status -->
    <div class="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg mb-2">
      <div :class="[
        'w-3 h-3 rounded-full',
        isConnected ? 'bg-green-500' : 'bg-red-500'
      ]"></div>
      <span class="text-sm">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
      <div v-if="isAudioEnabled" class="ml-auto">
        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Audio On</span>
      </div>
    </div>

    <!-- Messages Container -->
    <div class="flex-1 overflow-y-auto px-4 py-2 space-y-3 min-h-[300px] max-h-[400px] border rounded-lg bg-gray-50">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="[
          'p-3 rounded-lg max-w-[80%]',
          msg.sender === 'user' ? 'bg-blue-500 text-white ml-auto' : 
          msg.sender === 'agent' ? 'bg-white text-gray-800' :
          'bg-gray-200 text-gray-600 text-sm text-center mx-auto'
        ]"
      >
        <div v-if="msg.sender !== 'system'" class="flex items-start gap-2">
          <div
            v-if="msg.sender === 'agent'"
            class="bg-center bg-no-repeat aspect-square bg-cover rounded-full h-6 w-6 flex-shrink-0"
            :style="{ backgroundImage: `url(${agentAvatar})` }"
          ></div>
          <div class="flex-1">
            <p class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>
            <p class="text-xs opacity-70 mt-1">{{ formatTime(msg.timestamp) }}</p>
          </div>
          <div
            v-if="msg.sender === 'user'"
            class="bg-center bg-no-repeat aspect-square bg-cover rounded-full h-6 w-6 flex-shrink-0"
            :style="{ backgroundImage: `url(${userAvatar})` }"
          ></div>
        </div>
        <div v-else>
          {{ msg.content }}
        </div>
      </div>
    </div>

    <!-- Audio Controls -->
    <div class="flex gap-2 px-4 py-2">
      <button
        v-if="!isAudioEnabled"
        @click="startAudio"
        :disabled="!isConnected"
        class="flex-1 bg-green-500 hover:bg-green-600 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg text-sm font-medium"
      >
        Start Audio
      </button>
      <button
        v-else
        @click="stopAudio"
        class="flex-1 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
      >
        Stop Audio
      </button>
    </div>

    <!-- Chat Input -->
    <div class="flex items-center px-4 py-3 gap-3 @container">
      <label class="flex flex-col min-w-40 h-12 flex-1">
        <div class="flex w-full flex-1 items-stretch rounded-xl h-full">
          <input
            v-model="message"
            placeholder="Ask me anything..."
            :disabled="!isConnected"
            class="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-text-primary focus:outline-0 focus:ring-0 border-none bg-bg-secondary focus:border-none h-full placeholder:text-text-secondary px-4 rounded-r-none border-r-0 pr-2 text-base font-normal leading-normal disabled:opacity-50"
            @keypress.enter="sendMessage"
          />
          <div class="flex border-none bg-bg-secondary items-center justify-center pr-4 rounded-r-xl border-l-0 !pr-2">
            <div class="flex items-center gap-4 justify-end">
              <button
                @click="sendMessage"
                :disabled="!isConnected || !message.trim()"
                class="min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-full h-8 px-4 bg-primary text-white text-sm font-medium leading-normal hidden @[480px]:block disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span class="truncate">Send</span>
              </button>
            </div>
          </div>
        </div>
      </label>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// Props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isConnected: {
    type: Boolean,
    default: false
  },
  isAudioEnabled: {
    type: Boolean,
    default: false
  }
})

const message = ref('')

const agentAvatar = "https://lh3.googleusercontent.com/aida-public/AB6AXuB9WWgemwMAqIH4PmxNrsG1-sLvxiJtO1B94vbNpp5w3y9yqIA10-SR9LzKYImSHv9OkYfhV4SuJ4aZ3hdmV3GPFDdqd8z6W3pTGPsB_2CTm3SLhIb4op0rLr1zpbou4xjwfegnVNxERGB7JEg6T6HPPHNEJOavWPOp0eMB8fVsXuPMmTcOQJsW2amlCIB7Fv0VBfxNz8MvXOM_rv_73Ls_qZ1M3lPBBeoSI6qFMjcR54jyMftdyYckt4lHJfaT6pmcHzcHQAgvvAY"
const userAvatar = "https://lh3.googleusercontent.com/aida-public/AB6AXuDp1kg-Yfif67FuqEkbIO3VZbIDlRvHKW-8cuLvAX_wyyoBavqNzqXNZJo3Vq5ZIKKu-V4H0XmcO-rEk9kLL7sxtIUQPuO8zsM0iCpjbNS0xBZsz2B6Kc93LadJGz5jn0mEvKbrL4PpcHH2ARBTRiL2PMY-WmhI-swPnkcBe4dWD8XKt2Q1OyGf7s1KKRcCJvZMknlx8862xMY41t56NmSvj5jnIJMlxY0hn87v42Betz3dgh_Hu_odHhWsTLP-RMoXuSEEW24sgp4"

const emit = defineEmits(['send-message', 'start-audio', 'stop-audio'])

const sendMessage = () => {
  if (message.value.trim() && props.isConnected) {
    emit('send-message', message.value)
    message.value = ''
  }
}

const startAudio = () => {
  emit('start-audio')
}

const stopAudio = () => {
  emit('stop-audio')
}

const formatTime = (timestamp) => {
  return timestamp.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })
}
</script>