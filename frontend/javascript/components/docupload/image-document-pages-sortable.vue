<script setup>
/* This is a separate component because we need to provide Vue3 composition setup for useSortable,
which looks like the most reasonable replacement for vuedraggable (Vue2 only);
other alternatives did not work (vuedraggable-next and a different thin SortableJS wrapper). */

import { useSortable } from '@vueuse/integrations/useSortable'
import { computed, ref } from 'vue'
import ImagePage from './image-page.vue'
import { useAttachments } from './lib/attachments'

const { attachments, splitPages, rotatePage } = useAttachments()

const props = defineProps({
  idx: Number,
  showRotate: Boolean,
  showSplit: Boolean
})

const busy = computed(() => attachments.images[props.idx]?.isConverting)

const pages = computed({
  get: () => attachments.images[props.idx]?.pages || [],
  set: (val) => attachments.images[props.idx].pages = val
})

const pagesEl = ref()

useSortable(pagesEl, pages, { animation: 200 })
</script>

<template>
  <div
    ref="pagesEl"
    class="pages d-flex flex-wrap row-gap-5 column-gap-3 my-5"
    :class="{ 'pe-none': busy, 'opacity-50': busy}"
    >
    <image-page
      v-for="(page, pageNum) in pages"
      :key="page.id"
      :page="page"
      :page-num="pageNum + 1"
      :page-count="pages.length"
      :show-rotate="showRotate"
      :show-split="showSplit"
      @splitpages="splitPages(idx, pageNum + 1)"
      @rotatepage="rotatePage(page)" />
  </div>
</template>
