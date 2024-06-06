<script setup>
import { computed, defineEmits, onMounted } from 'vue'
import I18nMixin from '../../lib/i18n-mixin.js'

const props = defineProps({
  config: Object,
  document: Object
})

// adapt Vue2 mixin to Vue3; TODO maybe reactive()?
const i18n = computed(() => I18nMixin.computed.i18n.bind(props)())

const emit = defineEmits(['docupdated'])

const attachment = computed(() => props.document.attachment)

const canDelete = computed(
  () =>
    !!attachment.value &&
    attachment.value.can_delete &&
    !props.document.approving
)

const deleteAttachment = () => {
  if (false === window.confirm(i18n.value.confirmDelete)) return
  emit('docupdated', { deleting: true })
}

const renameAttachment = () => {
  // TODO
  console.error('not implemented')
}

onMounted(() => {
  // debugger
})
</script>

<template>
  <div>
    <!--TODO a11y-->
    <button
      class="btn btn-outline-dark me-1"
      disabled
      @click="renameAttachment">
      <i class="fa fa-pencil" />
    </button>
    <button
      class="btn btn-outline-dark"
      :disabled="!canDelete"
      @click="deleteAttachment">
      <i class="fa fa-trash" />
    </button>
  </div>
</template>
