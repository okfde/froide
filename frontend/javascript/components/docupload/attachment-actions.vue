<script setup>
import { computed, inject, nextTick, ref } from 'vue'
import { useAttachments } from './lib/attachments';
const { attachments, refresh: refreshAttachments, createDocument, deleteAttachment, approveAttachment, makeRelevant, getRedactUrl } = useAttachments()

import BsModal from '../bs-modal.vue'
// TODO linter wrong?
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import PdfRedaction from '../redaction/pdf-redaction.vue'

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

const emit = defineEmits(['actionDelete', 'actionDone'])

const config = inject('config')

const i18n = inject('i18n')

const unredacted = computed(() => attachment.resource_uri
  ? attachments.getUnredactedAttachmentByResourceUri(attachment.resource_uri)
  : null
)

const unconverted = computed(() => attachment.resource_uri
  ? attachments.getUnconvertedAttachmentByResourceUri(attachment.resource_uri)
  : null
)

const makeResult = () => {
  createDocument(attachment)
    .finally(() => {
      emit('actionDone')
    })
}

const dropdownHasItems = computed(() => attachment.canRedact || unredacted.value || unconverted.value)

const pdfRedaction = ref()

const pdfRedactionAtt = ref(null)

const pdfRedactionUploaded = () => {
  // handle v-if'ed modal
  pdfRedactionModal.value.hide()
  pdfRedactionAtt.value = null
  refreshAttachments()
  emit('actionDone')
}

const pdfRedactionModal = ref()

const redactClick = (evt, att) => {
  evt.preventDefault()
  // handle v-if'ed modal
  pdfRedactionAtt.value = att
  nextTick().then(() => pdfRedactionModal.value.show())
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
  approveAttachment(attachment)
    .then(() => emit('actionDone'))
}

</script>

<template>
  <button v-if="attachment.canMakeResult" @click="makeResult" type="button" class="btn btn-sm btn-link text-start"
    :class="{ disabled: attachment.creatingDocument }">
    <i class="fa fa-certificate"></i>
    {{ i18n.markResult }}
  </button>
  <a
    v-if="!dropdown && attachment.canRedact && !attachment.is_redacted"
    :href="getRedactUrl(attachment)"
    class="btn btn-sm btn-link text-start"
    @click="redactClick($event, attachment)"
    >
    <i class="fa fa-square"></i>
    {{ i18n.redact }}
  </a>
  <!-- TODO: this is not really schwärzung bearbeiten, but instead ungeschwärztes original noch mal schwärzen -->
  <a
    v-if="!dropdown && unredacted && unredacted.can_redact"
    :href="getRedactUrl(unredacted)"
    class="btn btn-sm btn-link text-start"
    @click="redactClick($event, unredacted)"
    >
    <i class="fa fa-pencil-square"></i>
    {{ i18n.editRedaction }}
  </a>
  <button v-if="attachment.is_irrelevant" @click="makeRelevantClick" type="button" class="btn btn-sm btn-link text-start">
    <i class="fa fa-exclamation-circle"></i>
    {{ i18n.markNotIrrelevant }}
  </button>
  <a class="btn btn-sm btn-link text-start" :href="attachment.file_url" :download="attachment.name">
    <i class="fa fa-download"></i>
    {{ i18n.download }}
  </a>
  <a v-if="!dropdown && unredacted" class="btn btn-sm btn-link text-start" :href="unredacted.file_url" download>
    <i class="fa fa-download"></i>
    {{ i18n.downloadUnredacted }}
  </a>
  <a v-if="!dropdown && unconverted" class="btn btn-sm btn-link text-start" :href="unconverted.file_url" download>
    <i class="fa fa-download"></i>
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
    <i class="fa fa-check"></i>
    <template v-if="config.foirequest.public"><!-- comment preserves the one whitespace from collapsing to match other items
      --> {{ i18n.makePublic }}
    </template>
    <template v-else><!--
      --> {{ i18n.approve }}
    </template>
  </button>
  <button v-if="attachment.canDelete" type="button" class="btn btn-sm btn-link text-start" @click="deleteClick">
    <i class="fa fa-trash"></i>
    {{ i18n.delete }}
  </button>
  <div v-if="dropdown && dropdownHasItems" :class="'dropdown ' + dropdownClasses">
    <button class="d-none d-md-block btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
      <span>{{ i18n.otherActions }}</span>
    </button>
    <button class="d-md-none btn btn-sm btn-light" type="button" data-bs-toggle="dropdown" aria-expanded="false">
      <i class="fa fa-ellipsis-h"></i>
    </button>
    <ul class="dropdown-menu">
      <li v-if="attachment.canRedact">
        <a class="dropdown-item" :href="getRedactUrl(attachment)">
          <i class="fa fa-square"></i>
          {{ i18n.redact }}
        </a>
      </li>
      <li v-if="unredacted && unredacted.can_redact">
        <a class="dropdown-item" :href="getRedactUrl(unredacted)">
          <i class="fa fa-pencil-square"></i>
          {{ i18n.editRedaction }}
        </a>
      </li>
      <li v-if="unredacted">
        <a class="dropdown-item" :href="unredacted.file_url" download>
          <i class="fa fa-download"></i>
          {{ i18n.downloadUnredacted }}
        </a>
      </li>
      <li v-if="unconverted">
        <a class="dropdown-item" :href="unconverted.file_url" download>
          <i class="fa fa-download"></i>
          {{ i18n.downloadOriginal }}
          <!-- TODO: show file extension / simplified filetype;
          XLS instead of application/vnd.mx-excel
          there is is_excel in attachment.py... -->
        </a>
      </li>
      <li v-if="attachment.canApprove">
        <button type="button" class="dropdown-item" @click="approveClick">
          <i class="fa fa-check"></i>
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
  <bs-modal
    v-if="pdfRedactionAtt"
    :key="pdfRedactionAtt.id"
    ref="pdfRedactionModal"
    dialog-classes="modal-dialog-scrollable ms-auto modal-xl modal-fullscreen-lg-down"
    content-classes="h-100"
    >
    <template #header>
      <h5 class="modal-title">
        {{ i18n.redact }}, {{ pdfRedactionAtt.name }}
      </h5>
    </template>
    <template #body>
      <pdf-redaction
        ref="pdfRedaction"
        :pdf-path="pdfRedactionAtt.file_url"
        :attachment-url="pdfRedactionAtt.anchor_url"
        :auto-approve="attachments.autoApproveSelection[pdfRedactionAtt.id] !== false"
        :post-url="
          config.url.redactAttachment.replace(
            '/0/',
            '/' + pdfRedactionAtt.id + '/'
          )
        "
        :approve-url="
          config.url.approveAttachment.replace(
            '/0/',
            '/' + pdfRedactionAtt.id + '/'
          )
        "
        :minimal-ui="true"
        :no-redirect="true"
        :can-publish="true"
        :config="config"
        @uploaded="pdfRedactionUploaded"
        ></pdf-redaction>
    </template>
    <template #footer>
      <button
        type="button"
        class="btn btn-primary"
        @click="pdfRedaction.redactOrApprove()"
        >{{ i18n.redactionDone }}</button>
    </template>
  </bs-modal>
</template>
