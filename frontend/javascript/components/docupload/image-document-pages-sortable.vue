<script setup>
/* This is a separate component because we need to provide Vue3 composition setup for useSortable,
which looks like the most reasonable replacement for vuedraggable (Vue2 only);
other alternatives did not work (vuedraggable-next and a different thin SortableJS wrapper). */

import { useSortable } from '@vueuse/integrations/useSortable'
import { computed, defineEmits, ref } from 'vue'
import ImagePage from './image-page.vue'

const props = defineProps({
  pages: Array,
  dense: Boolean
})

const pages = computed({
  get: () => props.pages,
  set: (val) => emit('resorted', val.map((page, i) => ({ ...page, pageNum: i + 1 })))
})

const emit = defineEmits(['resorted', 'pageupdated', 'splitpages'])

const pagesEl = ref()

useSortable(pagesEl, pages, { animation: 200 })
</script>

<template>
  <div ref="pagesEl" class="pages d-flex flex-wrap align-items-baseline pb-3">
    <image-page
      v-for="page in pages"
      :key="page.id"
      :page="page"
      :page-count="pages.length"
      :dense="dense"
      :hide-rotate="dense"
      :hide-split="dense"
      @pageupdated="emit('pageupdated', $event)"
      @splitpages="emit('splitpages', $event)" />
  </div>
</template>
