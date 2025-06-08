<template>
  <div class="layout-content-container flex flex-col w-80">
    <!-- AI Agent Chat Item -->
    <div class="flex items-center gap-4 bg-white px-4 min-h-[72px] py-2">
      <div
        class="bg-center bg-no-repeat aspect-square bg-cover rounded-full h-14 w-fit"
        :style="{ backgroundImage: `url(${agentAvatar})` }"
      ></div>
      <div class="flex flex-col justify-center">
        <p class="text-text-primary text-base font-medium leading-normal line-clamp-1">AI Agent</p>
        <p class="text-text-secondary text-sm font-normal leading-normal line-clamp-2">{{ currentTime }}</p>
      </div>
    </div>

    <!-- User Chat Item -->
    <div class="flex items-center gap-4 bg-white px-4 min-h-14">
      <div
        class="bg-center bg-no-repeat aspect-square bg-cover rounded-full h-10 w-fit"
        :style="{ backgroundImage: `url(${userAvatar})` }"
      ></div>
      <p class="text-text-primary text-base font-normal leading-normal flex-1 truncate">You</p>
    </div>

    <!-- Chat Input -->
    <div class="flex items-center px-4 py-3 gap-3 @container">
      <label class="flex flex-col min-w-40 h-12 flex-1">
        <div class="flex w-full flex-1 items-stretch rounded-xl h-full">
          <input
            v-model="message"
            placeholder="Ask me anything..."
            class="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-text-primary focus:outline-0 focus:ring-0 border-none bg-bg-secondary focus:border-none h-full placeholder:text-text-secondary px-4 rounded-r-none border-r-0 pr-2 text-base font-normal leading-normal"
            @keypress.enter="sendMessage"
          />
          <div class="flex border-none bg-bg-secondary items-center justify-center pr-4 rounded-r-xl border-l-0 !pr-2">
            <div class="flex items-center gap-4 justify-end">
              <button
                @click="sendMessage"
                class="min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-full h-8 px-4 bg-primary text-white text-sm font-medium leading-normal hidden @[480px]:block"
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
import { ref, computed } from 'vue'

const message = ref('')

const agentAvatar = "https://lh3.googleusercontent.com/aida-public/AB6AXuB9WWgemwMAqIH4PmxNrsG1-sLvxiJtO1B94vbNpp5w3y9yqIA10-SR9LzKYImSHv9OkYfhV4SuJ4aZ3hdmV3GPFDdqd8z6W3pTGPsB_2CTm3SLhIb4op0rLr1zpbou4xjwfegnVNxERGB7JEg6T6HPPHNEJOavWPOp0eMB8fVsXuPMmTcOQJsW2amlCIB7Fv0VBfxNz8MvXOM_rv_73Ls_qZ1M3lPBBeoSI6qFMjcR54jyMftdyYckt4lHJfaT6pmcHzcHQAgvvAY"
const userAvatar = "https://lh3.googleusercontent.com/aida-public/AB6AXuDp1kg-Yfif67FuqEkbIO3VZbIDlRvHKW-8cuLvAX_wyyoBavqNzqXNZJo3Vq5ZIKKu-V4H0XmcO-rEk9kLL7sxtIUQPuO8zsM0iCpjbNS0xBZsz2B6Kc93LadJGz5jn0mEvKbrL4PpcHH2ARBTRiL2PMY-WmhI-swPnkcBe4dWD8XKt2Q1OyGf7s1KKRcCJvZMknlx8862xMY41t56NmSvj5jnIJMlxY0hn87v42Betz3dgh_Hu_odHhWsTLP-RMoXuSEEW24sgp4"

const currentTime = computed(() => {
  return new Date().toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })
})

const emit = defineEmits(['send-message'])

const sendMessage = () => {
  if (message.value.trim()) {
    emit('send-message', message.value)
    message.value = ''
  }
}
</script>