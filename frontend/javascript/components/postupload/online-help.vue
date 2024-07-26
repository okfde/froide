<script setup>
import { watch, ref, onMounted } from 'vue'

const props = defineProps({
  path: String
})

const contents = ref('')

const isFetching = ref(false)

const fetchContents = (url) => {
  isFetching.value = true
  // TODO this is a hack to get going, we shall not parse html
  // remove once plain cms "api" lands
  return fetch(url)
    .then((response) => response.text())
    .then((response) => {
      contents.value = response
    })
    .catch((err) => {
      contents.value = 'Error: ' + err
    })
    .finally(() => {
      isFetching.value = false
    })
}

watch(
  () => props.path,
  (newPath) => {
    fetchContents(newPath)
  }
)

onMounted(() => {
  if (!props.path) return
  fetchContents(props.path)
})
</script>

<template>
  <div class="onlinehelp">
    <span class="spinner spinner-border" v-show="isFetching" />
    <div v-html="contents"></div>
  </div>
</template>

<style lang="scss" scoped>
.onlinehelp {
  background-color: transparentize(#fbde85, 0.05);
  min-height: 100%;
  padding: 4em 2em 2em 2em;
}
.spinner {
  position: absolute;
  left: calc(50% - var(--bs-spinner-width) / 2);
  top: calc(50% - var(--bs-spinner-height) / 2);
}
</style>
