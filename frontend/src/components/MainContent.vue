<template>
  <div class="layout-content-container flex flex-col max-w-[960px] flex-1">
    <!-- PDF Viewer -->
    <div v-if="currentDocument" class="flex-1 flex flex-col bg-gray-100 rounded-lg">
      <!-- PDF Header -->
      <div class="flex items-center justify-between p-4 bg-white rounded-t-lg border-b">
        <div class="flex items-center gap-3">
          <button 
            @click="closePDF"
            class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
          <h3 class="text-lg font-semibold text-gray-800">{{ currentDocument.filename }}</h3>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-600">{{ currentDocument.pageNumber ? `Page ${currentDocument.pageNumber}` : 'Document' }}</span>
        </div>
      </div>
      
      <!-- PDF iframe Container -->
      <div class="flex-1 overflow-hidden p-4">
        <iframe 
          :src="pdfUrl"
          class="w-full h-full border border-gray-300 shadow-lg bg-white rounded"
          title="PDF Viewer"
        ></iframe>
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
import { ref, computed } from 'vue'

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

function closePDF() {
  emit('select-item', null)
}
</script>