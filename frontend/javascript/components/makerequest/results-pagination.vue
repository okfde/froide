<script setup>

import { computed, inject } from 'vue'

const i18n = inject('i18n')

const { responseMeta } = defineProps({
  responseMeta: {
    type: Object,
    required: true
  },
})

const model = defineModel({ type: Object })

const show = computed(() => responseMeta?.total_count > responseMeta?.limit)

const pages = computed(() => {
  if (!responseMeta) {
    return [{ key: 'empty', label: '…' }]
  }
  // build an array like (current page = 5)
  // ← 1 2 … 4 5 6 … 41 42 →
  // previous/next are not special buttons, since all navigate by offset
  // TODO: when paginating, esp. using the next button,
  //   the "wobble" caused by the amount of pages shifting is pretty annoying --
  //   you can not just page through, buttons shift under your cursor
  const ret = [{
    key: 'previous',
    ariaHiddenLabel: '←',
    visuallyHiddenLabel: i18n.previous,
    offset: responseMeta.offset - responseMeta.limit,
    active: false,
    disabled: !responseMeta.previous,
  }]
  const current = Math.floor(responseMeta.offset / responseMeta.limit)
  const total = Math.ceil(responseMeta.total_count / responseMeta.limit)
  const nearFirstLast = 2
  const nearCurrent = 1
  let collapsing
  // iterate over all available pages...
  for (let p = 0; p < total; p++) {
    // ...pick those near first, last and current...
    if (p < nearFirstLast || p >= total - nearFirstLast || Math.abs(p - current) <= nearCurrent) {
      collapsing = false
      ret.push({
        key: p,
        label: p + 1,
        offset: p * responseMeta.limit,
        active: p === current,
        disabled: false,
        // TODO maybe hide the near ones on mobile so it does not wrap
      })
    } else {
      // ...collapse all others into ellipses.
      if (!collapsing) {
        collapsing = true
        ret.push({
          key: p,
          ariaHiddenLabel: '…',
          disabled: true,
          active: false,
        })
      }
    }
  }
  ret.push({
    key: 'next',
    ariaHiddenLabel: '→',
    visuallyHiddenLabel: i18n.next,
    offset: responseMeta.offset + responseMeta.limit,
    active: false,
    disabled: !responseMeta.next,
  })
  return ret
})

</script>

<template>
  <nav :aria-label="i18n.pagination" v-show="show">
    <ul class="pagination flex-wrap">
      <li class="page-item"
        v-for="page in pages"
        :key="page.key"
        :class="{
          active: page.active,
          disabled: page.disabled
        }"
        >
        <span
          class="page-link"
          @click="model.offset = page.offset"
          >
          <span v-if="page.ariaHiddenLabel" aria-hidden="true">{{ page.ariaHiddenLabel }}</span>
          <span v-if="page.visuallyHiddenLabel" class="visually-hidden">{{ page.visuallyHiddenLabel }}</span>
          <span v-if="page.label">{{ page.label }}</span>
        </span>
      </li>
    </ul>
  </nav>
</template>

<style scoped>

.page-item:not(.disabled) {
  cursor: pointer;
}

</style>