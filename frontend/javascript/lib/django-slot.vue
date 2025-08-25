<script lang="ts" setup>
import { onMounted, ref, inject } from 'vue'
import type { DjangoSlots } from './vue-helper'
import { registerBs } from './bootstrap-helpers'

const props = defineProps<{
  name: string,
  hasBsDirectives: boolean
}>()

const container = ref<HTMLDivElement | undefined>()

onMounted(() => {
  const djangoSlots: DjangoSlots = inject('django-slots')
  const fragment: DocumentFragment | undefined = djangoSlots?.[props.name]
  // save the parent element, after replaceWith we lose the reference
  const parent: HTMLElement | null | undefined = container.value?.parentElement

  if (fragment !== undefined) {
    container.value?.replaceWith(fragment.cloneNode(true))
    if (props.hasBsDirectives && parent) {
      registerBs(parent)
    }
  }
})
</script>

<template>
  <div ref="container" />
</template>
