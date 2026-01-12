<script lang="ts" setup>
import { onMounted, ref, inject } from 'vue'
import type { DjangoSlots } from './vue-helper'
import { registerBs } from './bootstrap-helpers'
import { registerOnlinehelpLinks } from './onlinehelp'

const props = defineProps<{
  name: string
  hasBsDirectives: boolean
  hasOnlinehelpLinks: boolean
}>()

const emit = defineEmits(['onlinehelpLinkClick'])

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
    if (props.hasOnlinehelpLinks && parent) {
      registerOnlinehelpLinks(parent, emit)
    }
  }
})
</script>

<template>
  <div ref="container" />
</template>
