<script lang="ts" setup>
import { onMounted, ref, inject } from 'vue'
import type { DjangoSlots } from './vue-helper'

const props = defineProps<{
  name: string
}>()

const container = ref<HTMLDivElement | undefined>()

onMounted(() => {
  const djangoSlots: DjangoSlots = inject('django-slots')
  const fragment: DocumentFragment | undefined = djangoSlots?.[props.name]

  if (fragment !== undefined) {
    container.value?.replaceWith(fragment.cloneNode(true))
  }
})
</script>

<template>
  <div ref="container" />
</template>
