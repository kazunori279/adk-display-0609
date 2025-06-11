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
          <span class="text-sm text-gray-600">Page {{ currentPage }} of {{ totalPages }}</span>
          <div class="flex gap-1">
            <button 
              @click="previousPage" 
              :disabled="currentPage <= 1"
              class="p-2 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed rounded"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
              </svg>
            </button>
            <button 
              @click="nextPage" 
              :disabled="currentPage >= totalPages"
              class="p-2 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed rounded"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      <!-- PDF Canvas Container -->
      <div class="flex-1 overflow-auto p-4">
        <div class="flex justify-center">
          <canvas 
            ref="pdfCanvas" 
            class="border border-gray-300 shadow-lg bg-white"
          ></canvas>
        </div>
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
import { ref, watch, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'

// Set up PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`

// Props
const props = defineProps({
  currentDocument: {
    type: Object,
    default: null
  }
})

// State
const contentItems = ref([])
const pdfCanvas = ref(null)
const currentPage = ref(1)
const totalPages = ref(0)
const pdfDocument = ref(null)
const renderTask = ref(null)

const emit = defineEmits(['select-item'])

const selectItem = (item) => {
  emit('select-item', item)
}

// PDF Loading and Rendering
async function loadPDF(documentInfo) {
  try {
    console.log('Loading PDF:', documentInfo)
    
    // Construct the PDF URL
    const pdfUrl = `${documentInfo.basePath}${documentInfo.filename}`
    console.log('PDF URL:', pdfUrl)
    
    // Load the PDF document
    const loadingTask = pdfjsLib.getDocument(pdfUrl)
    pdfDocument.value = await loadingTask.promise
    totalPages.value = pdfDocument.value.numPages
    
    // Set the initial page
    currentPage.value = documentInfo.pageNumber || 1
    
    // Render the page
    await renderPage(currentPage.value)
    
  } catch (error) {
    console.error('Error loading PDF:', error)
    // You might want to show an error message to the user
  }
}

async function renderPage(pageNum) {
  if (!pdfDocument.value || !pdfCanvas.value) return
  
  try {
    // Cancel any previous render task
    if (renderTask.value) {
      renderTask.value.cancel()
    }
    
    // Get the page
    const page = await pdfDocument.value.getPage(pageNum)
    
    // Set up the canvas
    const canvas = pdfCanvas.value
    const context = canvas.getContext('2d')
    
    // Calculate scale to fit the container nicely
    const containerWidth = canvas.parentElement.clientWidth - 40 // Account for padding
    const viewport = page.getViewport({ scale: 1.0 })
    const scale = Math.min(containerWidth / viewport.width, 1.5) // Max scale of 1.5
    const scaledViewport = page.getViewport({ scale })
    
    // Set canvas dimensions
    canvas.height = scaledViewport.height
    canvas.width = scaledViewport.width
    
    // Render the page
    const renderContext = {
      canvasContext: context,
      viewport: scaledViewport
    }
    
    renderTask.value = page.render(renderContext)
    await renderTask.value.promise
    renderTask.value = null
    
    console.log(`Rendered page ${pageNum} of ${totalPages.value}`)
    
  } catch (error) {
    if (error.name !== 'RenderingCancelledException') {
      console.error('Error rendering page:', error)
    }
  }
}

// Navigation functions
function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    renderPage(currentPage.value)
  }
}

function previousPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    renderPage(currentPage.value)
  }
}

function closePDF() {
  if (renderTask.value) {
    renderTask.value.cancel()
  }
  pdfDocument.value = null
  currentPage.value = 1
  totalPages.value = 0
  // You might want to emit an event to clear the currentDocument in the parent
  emit('select-item', null)
}

// Watch for document changes
watch(() => props.currentDocument, async (newDoc) => {
  if (newDoc) {
    await nextTick() // Wait for DOM to update
    await loadPDF(newDoc)
  }
}, { immediate: true })

// Watch for page changes to handle external page requests
watch(() => props.currentDocument?.pageNumber, (newPageNumber) => {
  if (newPageNumber && newPageNumber !== currentPage.value && pdfDocument.value) {
    currentPage.value = newPageNumber
    renderPage(currentPage.value)
  }
})
</script>