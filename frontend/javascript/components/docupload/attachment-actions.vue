<script setup>
import { computed, inject, ref } from 'vue'
import { useAttachments } from './lib/attachments';
const { attachments, createDocument, deleteAttachment, approveAttachment, makeRelevant, getRedactUrl } = useAttachments()

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

const canDelete = computed(() => attachment.can_delete && !attachment.approving)

const canRedact = computed(() => attachment.can_redact)

const isMakingResult = ref(false)

const canMakeResult = computed(() => {
  if (!config.settings.can_make_document) {
    return false
  }
  return !attachment.document && // not yet made result
    attachment.approved &&
    attachment.is_pdf &&
    !attachment.redacted &&
    !attachment.converted
})

const makeResult = () => {
  createDocument(attachment)
    .finally(() => {
      isMakingResult.value = false
    })
}

const dropdownHasItems = computed(() => canRedact.value || unredacted.value || unconverted.value)

</script>

<template>
  <a v-if="canMakeResult" @click="makeResult" class="btn btn-sm btn-link text-start"
    :class="{ disabled: isMakingResult }">
    <i class="fa fa-certificate"></i>
    {{ i18n.markResult }}
  </a>
  <a v-if="!dropdown && canRedact" :href="getRedactUrl(attachment)" class="btn btn-sm btn-link text-start">
    <i class="fa fa-square"></i>
    {{ i18n.redact }}
  </a>
  <!-- TODO: this is not really schwärzung bearbeiten, but instead ungeschwärztes original noch mal schwärzen -->
  <a v-if="!dropdown && unredacted && unredacted.can_redact" :href="getRedactUrl(unredacted)" class="btn btn-sm btn-link text-start">
    <i class="fa fa-pencil-square"></i>
    {{ i18n.editRedaction }}
  </a>
  <a v-if="attachment.is_irrelevant" @click="makeRelevant(attachment)" class="btn btn-sm btn-link text-start">
    <i class="fa fa-exclamation-circle"></i>
    {{ i18n.markNotIrrelevant }}
  </a>
  <a class="btn btn-sm btn-link text-start" :href="attachment.file_url" download>
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
  <a v-if="canDelete" class="btn btn-sm btn-link text-start" @click="deleteAttachment(attachment)">
    <i class="fa fa-trash"></i>
    {{ i18n.delete }}
  </a>
  <div v-if="dropdown && dropdownHasItems" :class="'dropdown ' + dropdownClasses">
    <button class="d-none d-md-block btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
      <span>{{ i18n.otherActions }}</span>
    </button>
    <button class="d-md-none btn btn-sm btn-light" type="button" data-bs-toggle="dropdown" aria-expanded="false">
      <i class="fa fa-ellipsis-h"></i>
    </button>
    <ul class="dropdown-menu">
      <li v-if="canRedact">
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
      <li v-if="config.user.can_edit_approval && !attachment.approved">
        <button type="button" class="dropdown-item" @click="approveAttachment(attachment)">
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
</template>
