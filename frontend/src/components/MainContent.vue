<template>
  <div class="layout-content-container flex flex-col max-w-[960px] flex-1">
    <!-- PDF Viewer -->
    <div v-if="currentDocument" class="flex-1 overflow-hidden p-4">
      <iframe 
        :src="pdfUrl"
        class="w-full h-full border border-gray-300 shadow-lg bg-white rounded"
        title="PDF Viewer"
        @load="() => console.log('[MainContent] iframe loaded:', pdfUrl)"
      ></iframe>
      <!-- Debug info -->
      <div class="text-xs text-gray-500 mt-2">
        Debug: {{ pdfUrl }}
      </div>
    </div>

    <!-- Default Content Grid (when no PDF is displayed) -->
    <div v-else class="grid grid-cols-[repeat(auto-fit,minmax(158px,1fr))] gap-3 p-4">
      <div 
        v-for="item in contentItems" 
        :key="item.id"
        class="flex flex-col gap-3 pb-3"
      >
        <div
          class="w-full bg-center bg-no-repeat aspect-video bg-cover rounded-xl cursor-pointer transition-transform hover:scale-105"
          :style="{ backgroundImage: `url(${item.image})` }"
          @click="selectItem(item)"
        ></div>
        <p class="text-text-primary text-base font-medium leading-normal">{{ item.title }}</p>
      </div>
      
      <!-- No content message -->
      <div v-if="contentItems.length === 0" class="col-span-full text-center py-8">
        <p class="text-gray-500">No documents to display. Ask the AI to show you a document!</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// Props
const props = defineProps({
  currentDocument: {
    type: Object,
    default: null
  }
})

// State
const contentItems = ref([])

const emit = defineEmits(['select-item'])

const selectItem = (item) => {
  emit('select-item', item)
}

// Computed property for PDF URL
const pdfUrl = computed(() => {
  if (!props.currentDocument) return ''
  
  let url = `${props.currentDocument.basePath}${props.currentDocument.filename}`
  
  // Add page fragment if specified
  if (props.currentDocument.pageNumber) {
    url += `#page=${props.currentDocument.pageNumber}`
  }
  
  return url
})

// Debug watchers
watch(() => props.currentDocument, (newDoc, oldDoc) => {
  console.log('[MainContent] currentDocument changed:', { newDoc, oldDoc })
}, { deep: true })

watch(pdfUrl, (newUrl, oldUrl) => {
  console.log('[MainContent] pdfUrl changed:', { newUrl, oldUrl })
})
</script>