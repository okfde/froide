<script setup>
import { useSortable } from '@vueuse/integrations/useSortable'
import { computed, ref } from 'vue'
import ImagePage from './image-page.vue'
import { useAttachments } from './lib/attachments'

const { attachments } = useAttachments()

const props = defineProps({
  idx: {
    type: Number,
    required: true
  },
  showRotate: Boolean,
  showSplit: Boolean
})

const busy = computed(() => attachments.images[props.idx]?.isConverting)

const pages = computed({
  get: () => attachments.images[props.idx]?.pages || [],
  set: (val) => (attachments.images[props.idx].pages = val)
})

const pagesEl = ref()

useSortable(pagesEl, pages, { animation: 200 })
</script>

<template>
  <div
    ref="pagesEl"
    class="pages d-flex flex-wrap row-gap-5 column-gap-3 my-5"
    :class="{ 'pe-none': busy, 'opacity-50': busy }"
  >
    <ImagePage
      v-for="(page, pageNum) in pages"
      :key="page.id"
      :idx="idx"
      :page="page"
      :page-num="pageNum + 1"
      :page-count="pages.length"
      :show-rotate="showRotate"
      :show-split="showSplit"
    />
  </div>
</template>
