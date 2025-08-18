<script setup>

import { inject } from 'vue'
import DjangoSlot from '../../lib/django-slot.vue'
import AttachmentsTable from '../docupload/attachments-table.vue'
import { useAttachments } from '../docupload/lib/attachments'

const i18n = inject('i18n')

const { attachments } = useAttachments()

const props = defineProps({
  message: Object
})

</script>

<template>
  <div class="container">
    <div class="row justify-content-center">
      <div class="col-lg-9">
        <div class="my-5 justify-content-center">
          <h1>{{ i18n.newReply }}</h1>
          <div
            v-if="attachments.redactNudgable.length === 0"
            class="alert alert-warning"
            role="alert"
            ><DjangoSlot name="email_intro_noattachments"></DjangoSlot>
          </div>

          <!-- markup and comments match template foirequest/body/message/message.html -->
          <div class="alpha-message alpha-message--expanded border mb-4">
            <div class="d-flex p-3 alpha-message__head">
              <!-- avatar -->
              <div class="alpha-message__avatar alpha-message__avatar--house">
                <i class="fa fa-bank" aria-hidden="true"></i>
              </div>
              <!-- sender, recipient, message preview, meta infos -->
              <div class="d-flex flex-fill flex-column overflow-hidden">
                <div class="d-flex justify-content-between align-items-center">
                  <!-- sender -->
                  <DjangoSlot name="message_sender"></DjangoSlot>
                  <!-- icons & timestamp -->
                  <div class="d-flex flex-nowrap">
                    <!-- need v-show, not v-if for tooltip -->
                    <span class="alpha-message__badge"
                      v-show="attachments.all.length > 0"
                      data-bs-toggle="tooltip"
                      :title="i18n.hasAttachments"
                      ><span class="fa fa-paperclip" aria-hidden="true"></span></span>
                    <span class="alpha-message__badge alpha-message__badge--error"
                      v-if="props.message.fails_authenticity"
                      data-bs-toggle="tooltip"
                      :title="i18n.possibleAuthenticityProblems"
                      ><span class="fa fa-user-secret"></span></span>
                    <span class="alpha-message__badge alpha-message__badge--kind"
                      v-if="props.message.is_escalation_message"
                      data-bs-toggle="tooltip"
                      :title="i18n.messageMediationAuthority"
                      ><span class="fa fa-shield"></span></span>
                    <span class="alpha-message__badge"
                      v-if="props.message.content_hidden"
                      data-bs-toggle="tooltip"
                      :title="i18n.messageNotYetPublic"
                      ><span class="fa fa-lock" aria-hidden="true"></span></span>
                    <!-- relative time -->
                    <span
                      class="alpha-message__relative-time d-flex align-items-center text-nowrap smaller text-gray-600"
                      data-bs-toggle="tooltip"
                      :title="props.message_timestamp_local">
                      {{ props.message_timestamp_relative }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div class="alpha-message__body">
              <div class="alpha-message__wrap alpha-message__bodyinner">
                <div
                  v-if="props.message.content_hidden"
                  class="alert alert-warning"
                  >
                  <DjangoSlot name="message_content_hidden"></DjangoSlot>
                </div>
                <div class="alpha-message__content-text">
                  <DjangoSlot name="message_content_redacted"></DjangoSlot>
                </div>
              </div>
              <div class="d-print-none alpha-message__toolbar alpha-message__toolbar--sticky alpha-message__toolbar--stickybump">
                <div class="alpha-message__wrap d-flex flex-column flex-sm-row flex-wrap justify-content-end py-2">
                  <!-- these buttons will trigger the modals+forms rendered outside of Vue component -->
                  <!-- Redact button -->
                  <DjangoSlot name="redactbutton"></DjangoSlot>
                  <!-- Edit button: omitted, because never can_edit email message -->
                  <!-- Problem button -->
                  <DjangoSlot name="problembutton"></DjangoSlot>
                </div>
              </div>
            </div>
          </div>

          <div class="p-3 bg-body-tertiary my-3">
            <div><strong>{{ i18n._('attachmentCount', { count : attachments.all.length }) }}</strong></div>
            <div v-if="attachments.convertable.length">
              {{ i18n.nextStepConvertImages }}
            </div>
            <div v-if="attachments.redactNudgable.length > 0">
              {{ i18n.nextStepReadRedact }}
            </div>
            <div
              v-if="attachments.havePendingConversion"
              class="alert alert-warning mt-2"
              >
              {{ i18n.pendingConversionWarning }}
            </div>
            <AttachmentsTable
              :subset="attachments.all"
              as-table-only
              badges-type
              dense
              />
          </div>

          <div class="my-3">
            <DjangoSlot name="email_request_link"></DjangoSlot>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>