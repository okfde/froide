<script setup>
import { computed, inject } from 'vue'
import { useAttachments } from './lib/attachments'
const {
  attachments,
  createDocument,
  deleteAttachment,
  approveAttachment,
  makeRelevant,
  getRedactUrl
} = useAttachments()

const { attachment, dropdown } = defineProps({
  attachment: Object,
  dropdown: {
    type: Boolean,
    default: false
  },
  dropdownClasses: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['actionDelete', 'actionDone', 'redactClick'])

const config = inject('config')

const i18n = inject('i18n')

const unredacted = computed(() =>
  attachment.resource_uri
    ? attachments.getUnredactedAttachmentByResourceUri(attachment.resource_uri)
    : null
)

const unconverted = computed(() =>
  attachment.resource_uri
    ? attachments.getUnconvertedAttachmentByResourceUri(attachment.resource_uri)
    : null
)

const makeResult = () => {
  createDocument(attachment).finally(() => {
    emit('actionDone')
  })
}

const dropdownHasItems = computed(
  () => attachment.canRedact || unredacted.value || unconverted.value
)

const redactClick = (evt, att) => {
  evt.preventDefault()
  emit('redactClick', att)
}

const deleteClick = () => {
  if (!window.confirm(i18n.value.confirmDelete)) return
  emit('actionDelete')
  deleteAttachment(attachment)
  // can't .then-emit actionDone here because the component will be optimistically gone by then
  // and the modal's backdrop will remain in dom
}

const makeRelevantClick = () => {
  makeRelevant(attachment)
  emit('actionDone')
}

const approveClick = () => {
  if (!window.confirm(i18n.value.confirmApproveUnredacted)) return
  approveAttachment(attachment).then(() => emit('actionDone'))
}
</script>

<template>
  <button
    v-if="attachment.canMakeResult"
    @click="makeResult"
    type="button"
    class="btn btn-sm btn-link text-start"
    :class="{ disabled: attachment.isCreatingDocument }"
  >
    <i class="fa fa-certificate" aria-hidden="true"></i>
    {{ i18n.markResult }}
  </button>
  <a
    v-if="!dropdown && unredacted && unredacted.can_redact"
    :href="getRedactUrl(unredacted)"
    @click="redactClick($event, unredacted)"
    class="btn btn-sm btn-link text-start"
  >
    <!-- "restart redaction (from unredacted)" -->
    <i class="fa fa-square" aria-hidden="true"></i>
    {{ i18n.redact }}
  </a>
  <a
    v-if="!dropdown && attachment.canRedact"
    :href="getRedactUrl(attachment)"
    @click="redactClick($event, attachment)"
    class="btn btn-sm btn-link text-start"
  >
    <template v-if="unredacted && unredacted.can_redact">
      <!-- "continue redaction (keep past redactions)"
        TODO: not really "edit" because can't undo/remove past redactions -->
      <i class="fa fa-pencil-square" aria-hidden="true"></i>
      {{ i18n.editRedaction }}
    </template>
    <template v-else>
      <!-- "start redaction (not redacted yet)" -->
      <i class="fa fa-square" aria-hidden="true"></i>
      {{ i18n.redact }}
    </template>
  </a>
  <button
    v-if="attachment.is_irrelevant"
    @click="makeRelevantClick"
    type="button"
    class="btn btn-sm btn-link text-start"
  >
    <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
    {{ i18n.markNotIrrelevant }}
  </button>
  <button
    v-if="
      !attachment.is_irrelevant && attachment.is_image && !attachment.converted
    "
    @click="makeRelevantClick"
    type="button"
    class="btn btn-sm btn-link text-start"
  >
    <i class="fa fa-exclamation-circle"></i>
    <!-- these are not actually strictly irrelevant, but we use the language in the instruction above -->
    {{ i18n.markNotIrrelevant }}
  </button>
  <a
    class="btn btn-sm btn-link text-start"
    :href="attachment.file_url"
    :download="attachment.name"
  >
    <i class="fa fa-download" aria-hidden="true"></i>
    {{ i18n.download }}
  </a>
  <a
    v-if="!dropdown && unredacted"
    class="btn btn-sm btn-link text-start"
    :href="unredacted.file_url"
    download
  >
    <i class="fa fa-download" aria-hidden="true"></i>
    {{ i18n.downloadUnredacted }}
  </a>
  <a
    v-if="!dropdown && unconverted"
    class="btn btn-sm btn-link text-start"
    :href="unconverted.file_url"
    download
  >
    <i class="fa fa-download" aria-hidden="true"></i>
    {{ i18n.downloadOriginal }}
    <!-- TODO: show file extension / simplified filetype;
     XLS instead of application/vnd.mx-excel
     there is is_excel in attachment.py... -->
  </a>
  <button
    v-if="!dropdown && attachment.canApprove"
    :disabled="attachment.approving"
    type="button"
    class="btn btn-sm btn-link text-start"
    @click="approveClick"
  >
    <i class="fa fa-check" aria-hidden="true"></i>
    <template v-if="config.foirequest.public"
      ><!-- comment preserves the one whitespace from collapsing to match other items
      -->
      {{ i18n.makePublic }}
    </template>
    <template v-else
      ><!--
      -->
      {{ i18n.approve }}
    </template>
  </button>
  <button
    v-if="attachment.canDelete"
    type="button"
    class="btn btn-sm btn-link text-start"
    @click="deleteClick"
  >
    <i class="fa fa-trash" aria-hidden="true"></i>
    {{ i18n.delete }}
  </button>
  <div
    v-if="dropdown && dropdownHasItems"
    :class="'dropdown ' + dropdownClasses"
  >
    <button
      class="d-none d-md-block btn btn-sm btn-outline-secondary dropdown-toggle"
      type="button"
      data-bs-toggle="dropdown"
      aria-expanded="false"
    >
      <span>{{ i18n.otherActions }}</span>
    </button>
    <button
      class="d-md-none btn btn-sm btn-light"
      type="button"
      data-bs-toggle="dropdown"
      aria-expanded="false"
    >
      <i class="fa fa-ellipsis-h" aria-hidden="true"></i>
      <span class="sr-only">{{ i18n.otherActions }}</span>
    </button>
    <ul class="dropdown-menu">
      <li v-if="unredacted && unredacted.can_redact">
        <a
          class="dropdown-item"
          :href="getRedactUrl(unredacted)"
          @click="redactClick($event, unredacted)"
        >
          <!-- "restart redaction (from unredacted)" -->
          <i class="fa fa-square" aria-hidden="true"></i>
          {{ i18n.redact }}
        </a>
      </li>
      <li v-if="attachment.canRedact">
        <a
          class="dropdown-item"
          :href="getRedactUrl(attachment)"
          @click="redactClick($event, attachment)"
        >
          <template v-if="unredacted && unredacted.can_redact">
            <!-- "continue redaction (keep past redactions)"
              TODO: not really "edit" because can't undo/remove past redactions -->
            <i class="fa fa-pencil-square" aria-hidden="true"></i>
            {{ i18n.editRedaction }}
          </template>
          <template v-else>
            <!-- "start redaction (not redacted yet)" -->
            <i class="fa fa-square" aria-hidden="true"></i>
            {{ i18n.redact }}
          </template>
        </a>
      </li>
      <li v-if="unredacted">
        <a class="dropdown-item" :href="unredacted.file_url" download>
          <i class="fa fa-download" aria-hidden="true"></i>
          {{ i18n.downloadUnredacted }}
        </a>
      </li>
      <li v-if="unconverted">
        <a class="dropdown-item" :href="unconverted.file_url" download>
          <i class="fa fa-download" aria-hidden="true"></i>
          {{ i18n.downloadOriginal }}
          <!-- TODO: show file extension / simplified filetype;
          XLS instead of application/vnd.mx-excel
          there is is_excel in attachment.py... -->
        </a>
      </li>
      <li v-if="attachment.canApprove">
        <button type="button" class="dropdown-item" @click="approveClick">
          <i class="fa fa-check" aria-hidden="true"></i>
          <template v-if="config.foirequest.public">
            {{ i18n.makePublic }}
          </template>
          <template v-else>
            {{ i18n.approve }}
          </template>
        </button>
      </li>
      <!-- postpone until new message API can handle it?
      <li v-else-if="config.user.can_edit_approval && attachment.approved">
        <button type="button" class="dropdown-item" @click="unapproveAttachment(att, { approved: false })">
          <i class="fa fa-times"></i>
          <template v-if="config.foirequest.public">
            {{ i18n.makeNonPublic }}
            Nicht-öffentlich machen
          </template>
          <template v-else>
            {{ i18n.unapprove }}
            Freigabe zurücknehmen
          </template>
        </button>
      </li>
      -->
    </ul>
  </div>
</template>
