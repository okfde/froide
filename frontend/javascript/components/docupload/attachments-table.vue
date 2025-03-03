<script setup>

import { useAttachments } from './lib/attachments';

const { attachments, deleteAttachment } = useAttachments()

import { computed, inject, ref, watch } from 'vue'

import AttachmentIconPreview from './attachment-icon-preview.vue'
import AttachmentActions from './attachment-actions.vue'
import AttachmentBadgeFiletype from './attachment-badge-filetype.vue'

const i18n = inject('i18n')

const { subset, asCardThreshold, actions, actionDelete, cardsSelection, tableSelection, selectionButtons, selectionActions, badgesNew, badgesRedaction, badgesType, badgesResolution, cardsBgTransparent } = defineProps({
  subset: {
    type: Array,
    required: true
  },
  asCardThreshold: {
    type: Number,
    default: 6
  },
  actions: Boolean,
  actionDelete: {
    type: Boolean,
    default: false,
    validator (value, props) {
      // conflicts with actions
      return !value || (value && !props.actions)
    }
  },
  cardsSelection: Boolean,
  tableSelection: Boolean,
  selectionButtons: {
    type: Boolean,
    default: false,
    validator (value, props) {
      // needs selection
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  selectionActions: {
    type: Boolean,
    default: false,
    validator (value, props) {
      // batch actions need selection to make sense
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  badgesNew: Boolean,
  badgesRedaction: Boolean,
  badgesType: Boolean,
  badgesResolution: Boolean,
  cardsBgTransparent: Boolean
})

const asCards = computed(() => subset.length < asCardThreshold)

const selectAllEl = ref()

const selectAllState = computed(() => {
  if (attachments.selectedIds.size === 0) return false
  const subsetSelected = subset.map(_ => attachments.selectedIds.has(_.id))
  if (subsetSelected.every(_ => _)) return true
  if (subsetSelected.some(_ => _)) return undefined
  return false
})

const selectAll = () => attachments.selectSubset(subset)
const selectNone = () => attachments.unselectSubset(subset)

const selectAllClick = () => {
  if (selectAllState.value === true) {
    selectNone()
  } else {
    selectAll()
  }
}

const selectAllLabel = computed(() => {
  return (selectAllState.value === true)
    ? i18n.value.selectNone
    : i18n.value.selectAll
})

/* when asCard flips over/under threshold (when something is uploaded/deleted)
 * we need to prevent things being still selected without the possibility to
 * change the selection */
watch(asCards, (newValue) => {
  if ((newValue && !cardsSelection) || (!newValue && !tableSelection)) selectNone()
})

const toggleSelection = (from, id) => {
  if (from === 'table' && !tableSelection) return
  if (from === 'card' && !cardsSelection) return
  if (attachments.selectedIds.has(id)) {
    attachments.selectedIds.delete(id)
  } else {
    attachments.selectedIds.add(id)
  }
}

const isSelectionDeletable = computed(() => attachments.selected.length && 
  attachments.selected.every(att => att.can_delete && !att.approving)
)

const deleteSelected = async () => {
  if (!window.confirm(i18n.value.confirmDeleteBulk)) return
  for (const att of attachments.selected) {
    await deleteAttachment(att)
  }
}

</script>

<template>

  <div
    v-if="(asCards && cardsSelection) || (!asCards && tableSelection)"
    class="d-flex px-1 py-2"
    :class="{
      'bg-light': !asCards,
      'border-top': !asCards
    }"
    >
    <label v-if="!asCards" class="d-flex flex-grow pe-3 align-self-stretch">
      <input
        type="checkbox"
        ref="selectAllEl"
        :checked="selectAllState"
        :indeterminate.prop="selectAllState === undefined"
        @click="selectAllClick"
        />
      <span class="sr-only">{{ selectAllLabel }}</span>
    </label>
    <div v-if="selectionActions" class="d-flex flex-grow-1 justify-content-end">
      <!-- TODO, needs backend support
      <button type="button" class="btn btn-link fw-bold">
        {{  i18n.downloadSelected }}
      </button>
      -->
      <button type="button" class="btn btn-link fw-bold" :disabled="!isSelectionDeletable" @click="deleteSelected">
        {{ i18n.deleteSelected }}
      </button>
    </div>
    <div v-if="selectionButtons" class="d-flex flex-grow-1 justify-content-end">
      <button type="button" class="btn btn-link" @click="selectAll">
        {{ i18n.selectAll }}
      </button>
      <button type="button" class="btn btn-link" @click="selectNone">
        {{ i18n.selectNone }}
      </button>
    </div>
  </div>

  <!-- AS CARDS -->

  <div
    v-if="asCards"
    :class="cardsBgTransparent ? '' : 'bg-body-tertiary p-3 p-md-5'"
    >
    <slot name="before-cards"></slot>
    <div class="d-flex flex-row flex-wrap gap-5 justify-content-around justify-content-lg-start">
      <div
        v-for="att in subset" :key="att.id"
        class="d-flex flex-column px-md-1 py-1 position-relative align-items-center item--card"
        :class="{ 'bg-primary-subtle': attachments.selectedIds.has(att.id) }"
        @click.self="toggleSelection('card', att.id)"
        >
        <label
          v-if="cardsSelection"
          class="d-block py-2"
          >
          <input v-model="attachments.selectedIds" type="checkbox" :value="att.id" />
        </label>
        <attachment-icon-preview
          :attachment="att"
          big
          class="text-center pb-1"
          :actions="actions"
          />
        <div
          class="text-center mb-1"
          @click.self="toggleSelection('card', att.id)"
          >
          {{ att.document?.title || att.name }}
          <span v-if="badgesNew && att.new" class="badge text-bg-success"
            >{{ i18n.new }}</span>
        </div>
        <div
          v-if="badgesRedaction">
          <span
            v-if="att.is_redacted"
            class="badge text-bg-success"
            >{{ i18n.redacted }}</span>
          <span
            v-else
            class="badge text-bg-warning"
            >{{ i18n.nonRedacted }}</span>
        </div>
        <span
          v-if="badgesResolution && att.document"
          class="badge text-bg-success"
          >{{ i18n.resolution }}</span>
        <div
          v-if="badgesType">
          <attachment-badge-filetype
            :attachment="att"
            />
        </div>
        <button v-if="actionDelete && att.can_delete" type="button" class="btn btn-outline-secondary" @click="deleteAttachment(att)">
          <i class="fa fa-trash"></i>
          <span class="sr-only">{{ i18n.delete }}</span>
        </button>
        <div v-if="actions" class="d-flex flex-column align-items-start flex-grow-0 flex-shrink-1">
          <attachment-actions
            :attachment="att"
            :dropdown="false"
            dropdown-classes=""
            />
        </div>
        <slot name="after-card" :attachment="att"></slot>
      </div>
    </div>
    <slot name="after-cards"></slot>
  </div>

  <!-- AS TABLE/ROWS -->

  <div v-else>
    <slot name="before-table"></slot>
    <div
      v-for="att in subset" :key="att.id"
      class="d-flex flex-column px-md-1 py-1 position-relative flex-md-row align-items-md-center px-5"
      :class="{
        'bg-primary-subtle': attachments.selectedIds.has(att.id),
        'border-top': subset.length > 1
      }"
      @click.self="toggleSelection('table', att.id)"
      >
      <label
        v-if="tableSelection"
        class="d-flex flex-grow ps-1 ps-md-0 pe-3 py-3 py-md-0 align-self-stretch position-absolute position-md-static top-0 start-0">
        <input v-model="attachments.selectedIds" type="checkbox" :value="att.id" />
      </label>
      <attachment-icon-preview
        :attachment="att"
        class="position-absolute position-md-static top-0 start-0 py-2 ps-2 pe-2 ps-md-0 ms-3 mt-1 ms-md-0"
        :actions="actions"
        />
      <div
        class="px-1 py-2 py-md-0 flex-md-grow-1"
        @click.self="toggleSelection('table', att.id)"
        >
        {{ att.document?.title || att.name }}
        <attachment-badge-filetype
          v-if="badgesType"
          :attachment="att"
          />
        <span
          v-if="badgesRedaction && att.is_redacted"
          class="badge text-bg-success"
          >{{ i18n.redacted }}</span>
        <span
          v-if="badgesResolution && att.document"
          class="badge text-bg-success"
          >{{ i18n.resolution }}</span>
        <span
          v-if="badgesRedaction && !att.is_redacted"
          class="badge text-bg-warning"
          >{{ i18n.nonRedacted }}</span>
      </div>
      <button
        v-if="actionDelete && att.can_delete"
        type="button"
        class="btn btn-outline-secondary position-absolute position-md-static top-0 end-0 mt-1 mt-md-0"
        @click="deleteAttachment(att)"
        >
        <i class="fa fa-trash"></i>
        <span class="sr-only">{{ i18n.delete }}</span>
      </button>
      <div
        v-if="actions"
        class="d-flex flex-grow-0 flex-shrink-1 justify-content-end"
        >
        <attachment-actions
          :attachment="att"
          :dropdown="true"
          dropdown-classes="position-absolute position-md-static top-0 end-0 mt-1 mt-md-0 d-flex align-items-center"
          />
      </div>
      <slot name="after-row" :attachment="att"></slot>
    </div>
    <slot name="after-table"></slot>
  </div>
</template>

<style scoped>

.item--card {
  width: 15em;
}

</style>