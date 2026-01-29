<script setup>
import { useAttachments } from './lib/attachments'

const {
  attachments,
  approveAttachment,
  deleteAttachment,
  createDocument,
  refresh: refreshAttachments
} = useAttachments()

import { computed, inject, nextTick, ref, watch } from 'vue'

import AttachmentIconPreview from './attachment-icon-preview.vue'
import AttachmentActions from './attachment-actions.vue'
import AttachmentBadges from './attachment-badges.vue'
import PdfRedactionModal from './pdf-redaction-modal.vue'

const i18n = inject('i18n')

const {
  subset,
  asCardThreshold,
  actions,
  actionDelete,
  cardsSelection,
  tableSelection,
  selectionButtons,
  selectionActionApprove,
  selectionActionDelete,
  selectionActionMakeResult,
  nudgeRedaction,
  badgesNew,
  badgesRedaction,
  badgesType,
  badgesResolution,
  cardsBgTransparent,
  dense
} = defineProps({
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
    validator(value, props) {
      // conflicts with actions
      return !value || (value && !props.actions)
    }
  },
  cardsSelection: Boolean,
  tableSelection: Boolean,
  selectionButtons: {
    type: Boolean,
    default: false,
    validator(value, props) {
      // needs selection
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  selectionActionDelete: {
    type: Boolean,
    default: false,
    validator(value, props) {
      // batch actions need selection to make sense
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  selectionActionApprove: {
    type: Boolean,
    default: false,
    validator(value, props) {
      // batch actions need selection to make sense
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  selectionActionMakeResult: {
    type: Boolean,
    default: false,
    validator(value, props) {
      // batch actions need selection to make sense
      return !value || (value && (props.cardsSelection || props.tableSelection))
    }
  },
  nudgeRedaction: Boolean,
  badgesNew: Boolean,
  badgesRedaction: Boolean,
  badgesType: Boolean,
  badgesResolution: Boolean,
  cardsBgTransparent: Boolean,
  dense: Boolean
})

const asCards = ref(subset.length < asCardThreshold)

watch(
  () => subset.length,
  (newLength, oldLength) => {
    if (newLength > oldLength && newLength >= asCardThreshold) {
      asCards.value = false
    }
  }
)

/* when asCard flips over/under threshold (when something is uploaded/deleted)
 * we need to prevent things being still selected without the possibility to
 * change the selection */
watch(asCards, (newValue) => {
  if ((newValue && !cardsSelection) || (!newValue && !tableSelection))
    selectNone()
})

/* pdf redaction */

const redactClick = (att) => {
  pdfRedactionAtt.value = att
  nextTick().then(() => pdfRedactionModal.value.show())
}

const pdfRedactionAtt = ref(null)
const pdfRedactionModal = ref()

const pdfRedactionUploaded = () => {
  pdfRedactionAtt.value = null
  refreshAttachments()
}

/* selection + bulk actions */

const selected = computed(() =>
  subset.filter((_) => attachments.selectedIds.has(_.id))
)

const selectAllEl = ref()

const selectAllState = computed(() => {
  if (attachments.selectedIds.size === 0) return false
  if (selected.value.length === subset.length) return true
  if (selected.value.length > 0) return undefined
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
  return selectAllState.value === true
    ? i18n.value.selectNone
    : i18n.value.selectAll
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

const isSelectionApprovable = computed(
  () => selected.value.length && selected.value.every((att) => att.canApprove)
)

const isSelectionDeletable = computed(
  () => selected.value.length && selected.value.every((att) => att.canDelete)
)

const isSelectionMakeResultable = computed(
  () =>
    selected.value.length && selected.value.every((att) => att.canMakeResult)
)

const approveSelected = async () => {
  if (!window.confirm(i18n.value.confirmApproveBulk)) return
  for (const att of selected.value) {
    await approveAttachment(att)
  }
}

const deleteSelected = async () => {
  if (!window.confirm(i18n.value.confirmDeleteBulk)) return
  for (const att of selected.value) {
    await deleteAttachment(att)
  }
}

const makeResultSelected = async () => {
  if (!window.confirm(i18n.value.confirmMakeResultBulk)) return
  for (const att of selected.value) {
    await createDocument(att)
  }
}
</script>

<template>
  <div
    v-if="(asCards && cardsSelection) || (!asCards && tableSelection)"
    class="d-flex px-1 py-2"
    :class="{
      'bg-body-tertiary': !asCards,
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
    <div class="d-flex flex-column flex-md-row flex-grow-1 justify-content-end">
      <!-- TODO bulk download button, needs backend support -->
      <div class="d-none d-md-block">
        <div class="btn-group" role="group">
          <button
            v-if="selectionActionDelete && isSelectionDeletable"
            type="button"
            class="btn btn-link fw-bold text-start"
            @click="deleteSelected"
          >
            {{ i18n.deleteSelected }}
          </button>
          <button
            v-if="selectionActionApprove"
            type="button"
            class="btn btn-link fw-bold text-start"
            :disabled="!isSelectionApprovable"
            @click="approveSelected"
          >
            {{ i18n.approveSelected }}
          </button>
          <button
            v-if="selectionActionMakeResult"
            type="button"
            class="btn btn-link fw-bold text-start"
            :disabled="!isSelectionMakeResultable"
            @click="makeResultSelected"
          >
            {{ i18n.markResultSelected }}
          </button>
        </div>
      </div>
      <div class="btn-group d-md-none align-self-end" role="group">
        <button
          type="button"
          class="btn btn-link dropdown-toggle"
          data-bs-toggle="dropdown"
          aria-expanded="false"
        >
          {{ i18n.selection }}
        </button>
        <ul class="dropdown-menu">
          <button
            v-if="selectionActionDelete && isSelectionDeletable"
            type="button"
            class="dropdown-item"
            @click="deleteSelected"
          >
            {{ i18n.deleteSelected }}
          </button>
          <button
            v-if="selectionActionApprove"
            type="button"
            class="dropdown-item"
            :disabled="!isSelectionApprovable"
            @click="approveSelected"
          >
            {{ i18n.approveSelected }}
          </button>
          <button
            v-if="selectionActionMakeResult"
            type="button"
            class="dropdown-item"
            :disabled="!isSelectionMakeResultable"
            @click="makeResultSelected"
          >
            {{ i18n.markResultSelected }}
          </button>
        </ul>
      </div>
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
    :class="
      cardsBgTransparent
        ? ''
        : 'bg-body-tertiary ' + (dense ? 'px-1' : 'px-3 px-md-5')
    "
  >
    <div class="py-3"><slot name="before-cards"></slot></div>
    <div
      :class="`d-flex flex-row flex-wrap gap-${dense ? 1 : 5} justify-content-around justify-content-lg-start`"
    >
      <div
        v-for="att in subset"
        :key="att.id"
        class="d-flex flex-column px-md-1 py-1 position-relative align-items-center item--card"
        :class="{
          'bg-primary-subtle': attachments.selectedIds.has(att.id),
          'item--dense': dense
        }"
        @click.self="toggleSelection('card', att.id)"
      >
        <label v-if="cardsSelection" class="d-block py-2">
          <input
            v-model="attachments.selectedIds"
            type="checkbox"
            :value="att.id"
          />
        </label>
        <AttachmentIconPreview
          v-bind="{ attachment: att, actions, nudgeRedaction }"
          :attachment="att"
          big
          class="text-center pb-1"
          @redact-click="redactClick"
        />
        <div class="text-center mb-1 mw-100 text-break">
          <AttachmentBadges
            v-bind="{
              attachment: att,
              badgesNew,
              badgesRedaction,
              badgesType,
              badgesResolution
            }"
            :attachment="att"
          />
        </div>
        <button
          v-if="actionDelete && att.canDelete"
          type="button"
          class="btn btn-sm btn-link"
          @click="deleteAttachment(att)"
        >
          <i class="fa fa-trash" aria-hidden="true"></i>
          {{ i18n.delete }}
        </button>
        <div
          v-if="actions"
          class="d-flex flex-column align-items-start flex-grow-0 flex-shrink-1"
        >
          <AttachmentActions
            :attachment="att"
            :dropdown="false"
            dropdown-classes=""
            @redact-click="redactClick"
          />
        </div>
        <slot name="after-card" :attachment="att"></slot>
      </div>
    </div>
    <slot name="after-cards"></slot>
    <div class="py-3 text-end">
      <button
        type="button"
        class="btn btn-link btn-sm"
        @click="asCards = false"
      >
        {{ i18n.displayAsTable }}
      </button>
    </div>
  </div>

  <!-- AS TABLE/ROWS -->

  <div v-else>
    <slot name="before-table"></slot>
    <div
      v-for="att in subset"
      :key="att.id"
      class="d-flex flex-column px-md-1 py-1 position-relative flex-md-row align-items-md-center px-5"
      :class="{
        'bg-primary-subtle': attachments.selectedIds.has(att.id),
        'border-top': subset.length > 1
      }"
      @click.self="toggleSelection('table', att.id)"
    >
      <label
        v-if="tableSelection"
        class="d-flex flex-grow ps-1 ps-md-0 pe-3 py-3 py-md-0 align-self-stretch position-absolute position-md-static top-0 start-0"
      >
        <input
          v-model="attachments.selectedIds"
          type="checkbox"
          :value="att.id"
        />
      </label>
      <AttachmentIconPreview
        v-bind="{ attachment: att, actions, nudgeRedaction }"
        class="start-0 py-2 ps-0 pe-2 ps-md-0 ms-0 mt-1 ms-md-0"
        @redact-click="redactClick"
      />
      <div
        class="flex-shrink-1 flex-grow-0 text-break d-md-flex flex-column align-items-start gap-1 me-md-auto"
      >
        <AttachmentBadges
          v-bind="{
            attachment: att,
            badgesNew,
            badgesRedaction,
            badgesType,
            badgesResolution
          }"
        />
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
        class="d-flex flex-column flex-sm-row flex-grow-0 flex-shrink-1 justify-content-end"
      >
        <AttachmentActions
          :attachment="att"
          :dropdown="true"
          dropdown-classes="position-absolute position-md-static top-0 end-0 mt-1 mt-md-0 d-flex align-items-center"
          @redact-click="redactClick"
        />
      </div>
      <slot name="after-row" :attachment="att"></slot>
    </div>
    <slot name="after-table"></slot>
    <div class="py-3 text-end border-top px-md-1">
      <button type="button" class="btn btn-link btn-sm" @click="asCards = true">
        {{ i18n.displayAsCards }}
      </button>
    </div>
  </div>
  <PdfRedactionModal
    ref="pdfRedactionModal"
    :attachment="pdfRedactionAtt"
    @uploaded="pdfRedactionUploaded"
  />
</template>

<style scoped>
.item--card {
  width: 15em;
}

.item--card.item--dense {
  width: 8em;
}
</style>
