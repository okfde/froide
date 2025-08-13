<script lang="ts" setup>
import { onMounted, ref, inject } from 'vue'
import { collapsePersistent } from './bootstrap-helpers'
import type { DjangoSlots } from './vue-helper'

const props = defineProps<{
  name: string
}>()

const container = ref<HTMLDivElement | undefined>()

onMounted(() => {
  const djangoSlots: DjangoSlots = inject('django-slots')
  const fragment: DocumentFragment | undefined = djangoSlots?.[props.name]
  // save the parent element, after replaceWith we lose the reference
  const parent: HTMLElement | null | undefined = container.value?.parentElement

  if (fragment !== undefined) {
    container.value?.replaceWith(fragment.cloneNode(true))
    // see also bootstrap.ts
    parent?.querySelectorAll<HTMLElement>('[data-bs-collapse-persistent]')
      .forEach((el) => collapsePersistent(el))
  }
})
</script>

<template>
  <div ref="container" />
</template>
