<script setup>

// import { useAttachmentsStore } from './lib/attachments-store'
import { useAttachments } from './lib/attachments';

const { attachments, deleteAttachment } = useAttachments()

import { computed, ref } from 'vue'

import AttachmentIconPreview from './attachment-icon-preview.vue'
import AttachmentActions from './attachment-actions.vue'

const { subset, cards, actions, multiActions, actionDelete, selection, selectionButtons, badgesNew, badgesRedaction } = defineProps({
  subset: {
    type: Array,
    default: () => []
  },
  cards: {
    type: Boolean,
    default: false
  },
  actions: {
    type: Boolean,
    default: false
  },
  multiActions: {
    type: Boolean,
    default: false
  },
  actionDelete: {
    type: Boolean,
    default: false
  },
  selection: {
    type: Boolean,
    default: false
  },
  selectionButtons: {
    type: Boolean,
    default: false
  },
  badgesNew: Boolean,
  badgesRedaction: Boolean
})

// const selectionIds = ref(new Set)
// const selection = computed(() => [...selectionIds.value].map(id => attachments.getById(id)))

const selectAllEl = ref()

// const selectAllState = computed(() => selectionIds.value.size === 0 ? false : (selectionIds.value.size === subset.length ? true : undefined))
const selectAllState = computed(() => {
  if (attachments.selectedIds.size === 0) return false
  const subsetSelected = subset.map(_ => attachments.selectedIds.has(_.id))
  if (subsetSelected.every(_ => _)) return true
  if (subsetSelected.some(_ => _)) return undefined
  // "subsecSelected.none"
  return false
})

const selectAll = () => subset.forEach(_ => attachments.selectedIds.add(_.id))
const selectNone = () => subset.forEach(_ => attachments.selectedIds.delete(_.id))

const selectAllClick = () => {
  if (selectAllState.value === true) {
    selectNone()
  } else {
    selectAll()
  }
}

const rowToggleSelection = (id) => {
  if (!multiActions) return
  if (attachments.selectedIds.has(id)) {
    attachments.selectedIds.delete(id)
  } else {
    attachments.selectedIds.add(id)
  }
}

/*const isSelectionDeletable = computed(() => selection.value.length && 
  selection.value.every(att => att.can_delete && !att.approving)
)*/
const isSelectionDeletable = computed(() => attachments.selected.length && 
  attachments.selected.every(att => att.can_delete && !att.approving)
)

const deleteSelected = async () => {
  // for (const att of selection.value) {
  for (const att of attachments.selected) {
    await deleteAttachment(att)
  }
}

</script>

<template>
  <!--pre>isD: {{ isSelectionDeletable }} / {{ selectionIds.map(id => attachments.getById(id)) }}</pre-->
  <div :class="cards ? 'd-flex flex-row flex-wrap gap-3' : ''">
    <div v-if="selection" class="d-none d-md-flex p-1 my-3">
      <label class="d-flex flex-grow pe-3 align-self-stretch">
        <input type="checkbox" ref="selectAllEl" :checked="selectAllState" :indeterminate.prop="selectAllState === undefined" @click="selectAllClick" />
      </label>
      <div v-if="multiActions" class="d-flex flex-grow-1 justify-content-end">
        <button type="button" class="btn btn-link fw-bold">
          Ausgewählte herunterladen
        </button>
        <button type="button" class="btn btn-link fw-bold" :disabled="!isSelectionDeletable" @click="deleteSelected">
          Ausgewählte löschen 
        </button>
      </div>
      <div v-if="selectionButtons" class="d-flex flex-grow-1 justify-content-end">
        <button type="button" class="btn btn-link" @click="selectAll">
          Alle auswählen
        </button>
        <button type="button" class="btn btn-link" @click="selectNone">
          Keine auswählen
        </button>
      </div>
    </div>
    <!-- ps-5 so icon can position-absolute itself in the upper left corner,
      and pe-5 for dropdown in upper right, resp. --> 
    <div v-for="att in subset" :key="att.id"
      :class="`d-flex flex-column px-md-1 py-1 position-relative my-3
        ${cards ? 'item--card' : 'flex-md-row align-items-md-center px-5'}`"
      @click.self="rowToggleSelection(att.id)"
      >
        <label v-if="selection" class="d-none d-md-flex flex-grow pe-3 align-self-stretch">
          <input v-model="attachments.selectedIds" type="checkbox" :value="att.id" />
        </label>
      <attachment-icon-preview
        :attachment="att"
        :size="cards ? '4em' : '2em'"
        :class="cards ? 'text-center pb-1' : 'position-absolute position-md-static top-0 start-0 py-2 ps-0'"
        />
      <div
        :class="cards ? 'text-center' : 'px-1 py-2 py-md-0 flex-md-grow-1'"
        @click.self="rowToggleSelection(att.id)"
        >
        {{ att.name }}
        <span v-if="badgesNew && att.new" class="badge text-bg-success">New</span>
      </div>
      <div
        v-if="badgesRedaction">
        <span
          v-if="att.is_redacted"
          class="badge text-bg-success"
          >geschwärzt</span>
        <span
          v-else
          class="badge text-bg-warning"
          >ungeschwärzt</span>
      </div>
      <!-- TODO too wide an small viewport -->
      <a v-if="actionDelete && att.can_delete" class="btn btn-outline-secondary" @click="deleteAttachment(att)">
        <i class="fa fa-trash"></i>
        <!--Löschen-->
      </a>
      <div v-if="actions" class="d-flex flex-column align-items-start flex-grow-0 flex-shrink-1"
        :class="{ 'flex-md-row': !cards, 'justify-content-md-end': !cards }">
        <attachment-actions
          :attachment="att"
          :dropdown="!cards"
          :dropdown-classes="cards ? '' : 'position-absolute position-md-static top-0 end-0'"
          />
      </div>
      <slot name="right" :attachment="att"></slot>
    </div>
  </div>
</template>

<style scoped>

.item--card {
  width: 16em;
}

</style>
