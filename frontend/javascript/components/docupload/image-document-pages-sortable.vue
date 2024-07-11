<script setup>
/* This is a separate component because we need to provide Vue3 composition setup for useSortable,
which looks like the most reasonable replacement for vuedraggable (Vue2 only);
other alternatives did not work (vuedraggable-next and a different thin SortableJS wrapper). */

import { useSortable } from '@vueuse/integrations/useSortable'
import { computed, defineEmits, ref } from 'vue'
import ImagePage from './image-page.vue'

const props = defineProps({ pages: Array })

// once updated to Vue>=3.4
// we might be able to simplify this to
//   const pages = defineModel()
// this is even more manual than supported by Vue3.2
// it was the only way to get the interaction with useSortable working
const pages = computed({
  get: () => props.pages,
  set: (val) => emit('update:pages', val)
})

const emit = defineEmits(['update:pages', 'pageupdated', 'splitpages'])

const pagesEl = ref()

useSortable(pagesEl, pages, { animation: 200 })
</script>

<template>
  <div ref="pagesEl" class="pages d-flex flex-nowrap align-items-baseline pb-3">
    <image-page
      v-for="page in pages"
      :key="page.id"
      :page="page"
      :page-count="pages.length"
      @pageupdated="emit('pageupdated', $event)"
      @splitpages="emit('splitpages', $event)" />
  </div>
</template>

<style lang="scss" scoped>
.pages {
  overflow: auto;
  overflow-x: scroll;
  overflow-scrolling: touch;
}
</style>
