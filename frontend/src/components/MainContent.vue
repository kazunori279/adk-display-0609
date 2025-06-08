<template>
  <div class="layout-content-container flex flex-col max-w-[960px] flex-1">
    <div class="grid grid-cols-[repeat(auto-fit,minmax(158px,1fr))] gap-3 p-4">
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
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const contentItems = ref([
  {
    id: 1,
    title: 'The Future of AI',
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCKf13lxQSJUOmTA5Cq-NejRGV_mnaq3zWw2NyEh5LqPDFeKWeGB8mq-afTokwKGDkRnhKOvrdaoxd5jPlDhcJYQ77HsXzh3ck59cG9yspo4khPXcrmM82siIyZwFUElJcDHjvOx2i6UY_6_As9htprCQHc_xRjo5Qbia2_VxBLtkKLGta5AxKq26PozBeoN8QIClvVE6cEpmD3Hh8JR7PRMvYmTVY76wMTKSKqI3phXvNJxbW_9r5-nuOcgFZ02jPfY-k3V4p4Obo'
  },
  // You can add more content items here
])

const emit = defineEmits(['select-item'])

const selectItem = (item) => {
  emit('select-item', item)
}
</script>