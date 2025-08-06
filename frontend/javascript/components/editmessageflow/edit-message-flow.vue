<script setup>
import { computed, defineProps, onMounted, provide, reactive, ref, watch } from 'vue'
import DjangoSlot from '../../lib/django-slot.vue'
import SimpleStepper from './simple-stepper.vue'
import PublicbodyChooser from '../publicbody/publicbody-beta-chooser'
import PdfRedaction from '../redaction/pdf-redaction.vue'
import { messageRetrieve, messagePartialUpdate, messagePublishCreate,
  requestRetrieve, requestPartialUpdate
  } from '../../api/index.ts'
import { guardBeforeunload, scrollNavIntoViewIfNecessary } from '../../lib/misc'
import { vBsTooltip } from '../../lib/vue-bootstrap'
import { useI18n } from '../../lib/i18n'
import { useIsDesktop } from '../../lib/vue-helpers-layout'
import { useAttachments } from '../docupload/lib/attachments'
import OnlineHelp from '../online-help.vue'
import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import ImageDocumentPagesSortable from '../docupload/image-document-pages-sortable.vue'
import AttachmentsTable from '../docupload/attachments-table.vue'

const props = defineProps({
  config: Object,
  message: Object,
  message_timestamp_relative: String,
  message_timestamp_local: String,
  schemas: Object,
  foirequest: Object,
  date_min: String,
  date_max: String,
  user_is_staff: Boolean,
  currency: String
})

const { i18n } = useI18n(props.config)
provide('i18n', i18n)
provide('config', props.config)

const {
  attachments,
  addFromUppy,
  refresh: refreshAttachments,
  refreshIfIdNotPresent: refreshAttachmentsIfIdNotPresent,
  convertImage,
  approveAllUnredactedAttachments,
  getWebsocketMessageRoom,
  monitorAttachments,
} = useAttachments({
  message: props.message,
  urls: {
    ...props.config.url,
    ...props.config.urls
  },
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  i18n
})

const { isDesktop } = useIsDesktop()

/* --- debug --- */

const debug = ref(!!localStorage.getItem('fds-editmessageflow-debug'))
window.FDSdebug = (val) => {
  debug.value = typeof val === 'boolean' ? val : !debug.value
  localStorage.setItem('fds-editmessageflow-debug', debug.value ? 'yes' : '')
}

const debugSkipDate = () => {
  values.date = document.forms.editmessageflow.elements.date.max
  values.registered_mail_date = document.forms.editmessageflow.elements.date.max
  updateValidity('date')
  updateValidity('registered_mail_date')
  gotoStep()
}

/* Form state */

const error = ref(false)

const values = reactive({})

const requestOldCosts = ref()
const requestHadCosts = ref()
const requestIsResolved = computed(() => values.status === 'resolved')
const requestWasResolved = ref()
const requestUpdateCosts = ref(false)
const messagePublicBodyIsDefault = ref(true)

const isSubmitting = ref(false)

const pickNotAutoApprove = ref(false)

/* Mobile App Content */

const mobileAppContent = ref(null)
const showMobileAppContent = ref(false)
if (props.config.url.mobileAppContent) {
  showMobileAppContent.value = true
  fetch(props.config.url.mobileAppContent.replace("{}", props.message.id))
    .then((response) => {
      if (!response.ok) {
        return i18n.value.error
      }
      return response.text()
    })
    .then((text) => {
      mobileAppContent.value = text
    })
}

/* Websocket connection */

if (props.config.url.messageWebsocket) {
  const room = getWebsocketMessageRoom() // new Room(props.config.url.messageWebsocket)
  room.connect().on('attachment_added', (data) => {
    // When a new attachment is added, refresh the attachments store.
    // We used to auto-step here, but this proved to error-prone,
    // 1 click more over potential confusion.
    refreshAttachmentsIfIdNotPresent(data.attachment)
  })
  // react to changes (when image attachments become available = not pending)
  monitorAttachments()
}

/* Form helpers */

const updateValuePublicBody = (pbUpdateEvt) => {
  // form some reason, this didn't work inline in the handler
  values.public_body = pbUpdateEvt.resourceUri
}

const requestResolutionChoices = computed(() => {
  // remove nonsensical combos
  const badCombinations = !values.is_response
    ? ['', 'successful', 'partially_successful', 'not_held', 'refused']
    : ['user_withdrew_costs']
  return props.schemas.resolution_choices.filter(
    (choice) => !badCombinations.includes(choice.value)
  )
})

const messageIsResponseChoices = [
  { value: true, label: i18n.value.messageReceivedLetter },
  { value: false, label: i18n.value.messageSentLetter }
]

const isoPrepareDate = (dateYmdStr) => {
  // From <input type="date"> we get a string .value like 'yyyy-mm-dd'
  // Note that .valueAsDate would have a similar problem:
  // "When the time zone offset is absent, date-only forms are interpreted as a UTC time
  // and date-time forms are interpreted as a local time."
  // We need to turn it into a timestamp:
  let dateTime = new Date(dateYmdStr) // this is "today 0:00", but UTC...
  // ...so it could be interpreted as a significantly different date
  // by serverside utils.postal_date on publish.
  // The server does not know client's timezone!
  // So we add a reasonable time, like (local) noon...
  const now = new Date
  const isToday = ymdifyDate(now) === dateYmdStr
  const isTodayAm = isToday && (now.getHours() < 12)
  if (isTodayAm) {
    // ...but not if noon is still in the future,
    // which would throw a validation error.
    // In "the AM" we basically return "now", rounded...
    dateTime.setHours(now.getHours(), now.getMinutes(), 0, 0)
  } else {
    // ...for any day in the past, we do set noon.
    dateTime.setHours(12, 0, 0, 0)
  }
  // Note that the logic above could lead to unexpected behavior between
  // "client midnight" and "server midnight".
  // Last, we avoid inventing a too early timestamp,
  // (request created in the pm, post uploaded same day)
  const requestCreatedAt = new Date(props.foirequest.created_at)
  if (dateTime < requestCreatedAt) {
    // "round up" a second, avoid precision collision
    dateTime = new Date((+requestCreatedAt) + 1000)
  }
  return dateTime.toISOString()
}

const ymdifyDate = (date) =>
  `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`

/* Form helpers, validity */

const validity = reactive({
  date: false,
  registered_mail_date: false,
  status: false,
  resolution: false
})

// TODO updateValidity should (maybe) be called on gotoStep(STEP_MESSAGE_DATE), too
const updateValidity = (key) => {
  let el = document.forms.editmessageflow.elements[key]
  // checkValidity is same for any radio button of a given name, we pick the first
  if (el instanceof RadioNodeList) el = el[0]
  // just assume true if browser doesn't support checkValidity
  validity[key] = 'checkValidity' in el ? el.checkValidity() : true
}

/* Form API interaction: retrieval */

const retrieveValues = async () => {
  const { data: request } = await requestRetrieve({
    path: { id: props.foirequest.id },
    throwOnError: true
  })
  values.status = request.status
  values.public_body = request.public_body.resource_uri
  requestOldCosts.value = request.costs
  requestHadCosts.value = parseFloat(request.costs) > 0
  values.costs = request.costs
  values.resolution = request.resolution
  // the 'resolved' magic string could be symbolically imported from api/types.gen.ts to be super clean...
  requestWasResolved.value = request.status === 'resolved'
  const { data: message } = await messageRetrieve({
    path: { id: props.message.id },
    throwOnError: true
  })
  values.is_response = message.is_response
  values.date = ymdifyDate(new Date(message.timestamp))
  values.registered_mail_date = message.registered_mail_date
    ? ymdifyDate(message.registered_mail_date)
    : ''
  values.sender_public_body = message.sender_public_body
  values.recipient_public_body = message.recipient_public_body
}

// note: even before onMounted!
retrieveValues()
  .catch((err) => {
    console.error('retrieveValues error', err)
    error.value = err
  })

/* Form API interaction: update/submit --- */

const requestUpdateValues = () => {
  return requestPartialUpdate({
    path: { id: props.foirequest.id },
    body: {
      costs: values.costs,
      status: values.status,
      resolution: values.resolution,
    },
    throwOnError: true
  })
}

const messageUpdateValues = () => {
  const messageBody = {
    is_response: values.is_response,
    sender_public_body: values.is_response ? values.public_body : null,
    recipient_public_body: values.is_response ? null : values.public_body,
  }
  if (values.date) messageBody.timestamp = isoPrepareDate(values.date)
  if (values.registered_mail_date) messageBody.registered_mail_date = isoPrepareDate(values.registered_mail_date)
  return messagePartialUpdate({
    path: { id: props.message.id },
    body: messageBody,
    throwOnError: true
  })
    .then(() => {
      console.info('messagePartialUpdate successful')
    })
}

const messagePublishDraft = () => {
  return messagePublishCreate({
    path: { id: props.message.id },
    throwOnError: true
  })
}

const approveAndPublish = async () => {
  isSubmitting.value = true
  try {
    // "flatten/reduce" the {id:bool} object into an array (where false!)
    const excludeIds = Object.entries(attachments.autoApproveSelection)
      .filter((kv) => kv[1] === false)
      .map((kv) => +kv[0])
    await approveAllUnredactedAttachments(excludeIds)
    await requestUpdateValues()
    if (!isEmailResponse) {
      await messageUpdateValues()
      await messagePublishDraft()
    }
    gotoStep()
  } catch (err) {
    // error from the partialUpdates/PATCHes looks like
    // { resolution: [ '"0" ist keine gültige Option'] }
    // { non_field_errors: [ 'Antwortnachrichten müssen...' ] }
    console.error('approveAndPublish error', err)
    error.value = err
  } finally {
    isSubmitting.value = false
  }
}

/* --- <OnlineHelp> interaction --- */

const onlineHelp = ref()

/* --- <AttachmentManager> interaction --- */

onMounted(() => {
  refreshAttachments()
})

// eslint-disable-next-line vue/no-side-effects-in-computed-properties
const attachmentsSelectedPdfRedaction = computed(() => attachments.selected
  .sort((a, b) => a.id - b.id)
)

const attachmentsImagesConverting = computed(() => attachments.isConverting)

const attachmentsConvertImages = () => {
  if (attachments.images.length === 0) {
    console.log('no images to convert')
    gotoStep()
    return
  }
  convertImage(0)
    .then(() => gotoStep())
    .catch((err) => {
      console.error(err)
      window.alert(`${i18n.value.error}: ${err.message}`)
    })
}

const attachmentsOverviewActions = ref(false)

/* --- <FileUploader> interaction --- */

const fileUploader = ref()
const fileUploaderShow = ref(false)
const fileUploaderUploading = ref(false)

watch(isDesktop, (newValue) => {
  if (newValue) fileUploaderShow.value = true
}, { immediate: true })

watch(() => attachments.images.length, (newValue, oldValue) => {
  if (newValue === 0 && oldValue > 0) {
    fileUploaderShow.value = true
  }
})

onMounted(() => {
  document.body.addEventListener('dragover', () => fileUploaderShow.value = true)
  document.body.addEventListener('dragenter', () => fileUploaderShow.value = true)
})

const fileUploaderUpload = () => {
  fileUploaderShow.value = true
  fileUploaderUploading.value = true
}

const uppyAdds = []

const fileUploaderSucceeded = (uppyResult) => {
  uppyAdds.push(addFromUppy(uppyResult, i18n.value.documentsUploadDefaultFilename))
}

const fileUploaderCompleted = async (uppyResult) => {
  await Promise.all(uppyAdds)
  fileUploaderUploading.value = false
  fileUploaderShow.value = false
  if (uppyResult.failed?.length > 0) return
  if (isDesktop.value) return
  gotoStep()
}

/* --- <PdfRedaction> interaction --- */

const pdfRedaction = ref()

const pdfRedactionCurrentIndex = computed(() => {
  // stepHistory can contain the same step multiple times;
  // we'll use the amount of the REDACT step implicitly to select the nth document for redaction
  const index1based = stepHistory.filter(
    (_) => _ === STEP_REDACTION_REDACT
  ).length
  if (index1based === 0) return false
  return index1based - 1
})
const pdfRedactionCurrentDoc = computed(() => {
  if (pdfRedactionCurrentIndex.value === false) return
  return attachmentsSelectedPdfRedaction.value[pdfRedactionCurrentIndex.value]
})

const pdfRedactionCurrentHasRedactions = ref(false)
const pdfRedactionProcessing = ref(false)
const pdfRedactionRedact = () => {
  pdfRedactionProcessing.value = true
  // XXX calling child's method
  // alternatively, could listen to an event
  pdfRedaction.value.redactOrApprove().then(() => {
    pdfRedactionProcessing.value = false
    pdfRedactionCurrentHasRedactions.value = false
    gotoStep()
  })
}
const pdfRedactionUploaded = () => {
  refreshAttachments()
}

/* --- state/flow --- */

const isEmailResponse = (props.message.kind === 'email' && props.message.is_response)

const questionTotal = isEmailResponse ? 2 : 5

const progressSteps = isEmailResponse
  ? [i18n.value.readAndRedact, i18n.value.enterInformation]
  : [i18n.value.upload, i18n.value.enterInformation, i18n.value.redact]

/* --- state machine, functionality --- */

const firstStep = isEmailResponse
  ? STEP_INTRO_EMAIL
  : STEP_INTRO
const stepHistory = reactive([firstStep])
const step = computed(() =>
  stepHistory.length ? stepHistory[stepHistory.length - 1] : false
)
const stepContext = computed(() => stepsConfig[step.value].context || {})

const gotoStep = async (nextStep) => {
  const onBeforeNext = stepsConfig[step.value].onBeforeNext
  if (onBeforeNext) {
    if (await onBeforeNext() === false) {
      console.warn('onBeforeNext returned false')
      scrollNavIntoViewIfNecessary()
      // or: scrollErrorAlertIntoViewIfNecessary
      return
    }
  }
  if (!nextStep)
    nextStep =
      typeof stepsConfig[step.value].next === 'function'
        ? stepsConfig[step.value].next()
        : stepsConfig[step.value].next
  stepHistory.push(nextStep)
  stepsConfig[nextStep].onEnter?.()
  scrollNavIntoViewIfNecessary()
}

const backStep = () => {
  stepsConfig[step.value].onBack?.()
  stepHistory.pop()
}

const isGotoValid = computed(() => {
  if ('isGotoValid' in stepContext.value) return stepContext.value.isGotoValid()
  return true
})

/* --- state machine, config: states, transitions --- */

// vuex mutation style constants/"symbols"
const STEP_INTRO = 'STEP_INTRO' // 1100
const STEP_INTRO_EMAIL = 'STEP_INTRO_EMAIL'
const STEP_DOCUMENTS_CONVERT = 'STEP_DOCUMENTS_CONVERT' // 1201
const STEP_DOCUMENTS_SORT = 'STEP_DOCUMENTS_SORT' // 1201
const STEP_DOCUMENTS_CONVERT_PDF = 'STEP_DOCUMENTS_CONVERT_PDF' // 1202
const STEP_DOCUMENTS_OVERVIEW = 'STEP_DOCUMENTS_OVERVIEW' // 1300
const STEP_MESSAGE_SENT_OR_RECEIVED = 'STEP_MESSAGE_SENT_OR_RECEIVED' // 2376
const STEP_MESSAGE_PUBLICBODY_CHECK = 'STEP_MESSAGE_PUBLICBODY_CHECK' // 2380
const STEP_MESSAGE_PUBLICBODY_UPDATE = 'STEP_MESSAGE_PUBLICBODY_UPDATE' // 2381
const STEP_MESSAGE_DATE = 'STEP_MESSAGE_DATE' // 2384
const STEP_MESSAGE_DATE_REGISTERED_MAIL = 'STEP_MESSAGE_DATE_REGISTERED_MAIL' // 2382
const STEP_MESSAGE_STATUS = 'STEP_MESSAGE_STATUS' // 2437
const STEP_MESSAGE_MESSAGE_RESOLUTION = 'STEP_MESSAGE_MESSAGE_RESOLUTION' // 2438
const STEP_MESSAGE_COST_CHECK_ANY = 'STEP_MESSAGE_COST_CHECK_ANY' // 2388
const STEP_MESSAGE_COST_CHECK_LAST = 'STEP_MESSAGE_COST_CHECK_LAST' // 2390
const STEP_REDACTION_PICKER = 'STEP_REDACTION_PICKER' // 3402
const STEP_REDACTION_REDACT = 'STEP_REDACTION_REDACT' // 3001
const STEP_DOCUMENTS_OVERVIEW_REDACTED = 'STEP_DOCUMENTS_OVERVIEW_REDACTED' // 4413
const STEP_MESSAGE_COST_UPDATE = 'STEP_MESSAGE_COST_UPDATE' // 2565
const STEP_OUTRO = 'STEP_OUTRO' // 4570

const stepsConfig = {
  [STEP_INTRO]: {
    next: () => {
      if (attachments.images.length) {
        return STEP_DOCUMENTS_SORT // dot:label="has images"
      }
      if (attachments.convertable.length > 0) {
        return STEP_DOCUMENTS_CONVERT // dot:label="has convertables"
      }
      console.log('uploads were documents, not images, passing by image sorting')
      return STEP_DOCUMENTS_OVERVIEW
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.addLetter
    }
  },
  [STEP_INTRO_EMAIL]: {
    next: () => {
      if (attachments.convertable.length > 0) {
        return STEP_DOCUMENTS_CONVERT // dot:style=dotted
      }
      else if (attachments.redactNudgable.length === 0) {
        return STEP_MESSAGE_STATUS // dot:style=dotted
      }
      console.log('uploads were documents, not images, passing by image sorting')
      return STEP_REDACTION_REDACT // dot:style=dotted
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.newReply
    }
  },
  [STEP_DOCUMENTS_CONVERT]: {
    next: () => {
      if (isEmailResponse) {
        return attachments.redactNudgable.length > 0
          ? STEP_REDACTION_REDACT // dot:style=dotted
          : STEP_MESSAGE_STATUS // dot:style=dotted
      }
      return STEP_DOCUMENTS_OVERVIEW
    },
    onEnter: () => {
      guardBeforeunload(true)
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: isEmailResponse
        ? i18n.value.readAndRedact
        : i18n.value.letterUploadOrScan
    }
  },
  [STEP_DOCUMENTS_SORT]: {
    next: STEP_DOCUMENTS_CONVERT_PDF,
    onEnter: () => {
      guardBeforeunload(true)
    },
    onBack: () => {
      // go back two steps, to INTRO
      // stepHistory.pop()
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: isEmailResponse
        ? i18n.value.readAndRedact
        : i18n.value.letterUploadOrScan
    }
  },
  [STEP_DOCUMENTS_CONVERT_PDF]: {
    next: () => {
      return isEmailResponse
        ? STEP_REDACTION_REDACT
        : STEP_DOCUMENTS_OVERVIEW
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: isEmailResponse
        ? i18n.value.readAndRedact
        : i18n.value.letterUploadOrScan
    }
  },
  [STEP_DOCUMENTS_OVERVIEW]: {
    next: STEP_MESSAGE_SENT_OR_RECEIVED,
    onEnter: () => {
      guardBeforeunload(true)
      pdfRedactionUploaded()
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: isEmailResponse
        ? i18n.value.readAndRedact
        : i18n.value.letterUploadOrScan
    }
  },
  [STEP_MESSAGE_SENT_OR_RECEIVED]: {
    next: STEP_MESSAGE_PUBLICBODY_CHECK,
    context: {
      // n/a for isEmailResponse
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: 1,
    }
  },
  [STEP_MESSAGE_PUBLICBODY_CHECK]: {
    next: () => {
      if (isDesktop.value) return STEP_MESSAGE_DATE
      return messagePublicBodyIsDefault.value
        ? STEP_MESSAGE_DATE
        : STEP_MESSAGE_PUBLICBODY_UPDATE
    },
    context: {
      // n/a for isEmailResponse
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: 2,
    }
  },
  [STEP_MESSAGE_PUBLICBODY_UPDATE]: {
    next: STEP_MESSAGE_DATE,
    context: {
      // n/a for isEmailResponse
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_MESSAGE_DATE]: {
    next: () => {
      if (isDesktop.value) return STEP_MESSAGE_STATUS
      return values.is_registered_mail
        ? STEP_MESSAGE_DATE_REGISTERED_MAIL
        : STEP_MESSAGE_STATUS
    },
    onEnter: () => {
      updateValidity('date')
      updateValidity('registered_mail_date')
    },
    context: {
      // n/a for isEmailResponse
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: 3,
      isGotoValid: () => {
        if (isDesktop.value && values.is_registered_mail)
          return validity.date && validity.registered_mail_date
        return validity.date
      }
    }
  },
  [STEP_MESSAGE_DATE_REGISTERED_MAIL]: {
    next: STEP_MESSAGE_STATUS,
    onEnter: () => {
      updateValidity('date')
      updateValidity('registered_mail_date')
    },
    context: {
      // n/a for isEmailResponse
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      isGotoValid: () => validity.registered_mail_date
    }
  },
  [STEP_MESSAGE_STATUS]: {
    next: () => {
      if (!isDesktop.value && requestIsResolved.value)
        return STEP_MESSAGE_MESSAGE_RESOLUTION // dot:label="mobile&unresolved"
      // TODO: replace all STEP_REDACTION_PICKER with `if uploadedDocuments.length === 1 ? ... : STEP_REDACTION_PICKER`
      // if is not response, can't have cost, so skip over the cost flow
      if (!values.is_response && !isEmailResponse) return STEP_REDACTION_PICKER // dot:label="no cost"
      return requestHadCosts.value
        ? STEP_MESSAGE_COST_CHECK_LAST
        : STEP_MESSAGE_COST_CHECK_ANY
    },
    onEnter: () => {
      updateValidity('status')
      updateValidity('resolution')
    },
    context: {
      progressStep: 1, // same for isEmailResponse, n.b. also "Step 2/2" next to mobileHeaderTitle
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: isEmailResponse ? 1 : 4,
      showPeekAttachments: isEmailResponse,
      isGotoValid: () => {
        if (isDesktop.value && requestIsResolved.value) {
          return validity.status && validity.resolution
        }
        return validity.status
      }
    }
  },
  [STEP_MESSAGE_MESSAGE_RESOLUTION]: {
    next: () => {
      if (!values.is_response && !isEmailResponse) return STEP_REDACTION_PICKER // dot:label="no cost"
      return requestHadCosts.value
        ? STEP_MESSAGE_COST_CHECK_LAST
        : STEP_MESSAGE_COST_CHECK_ANY
    },
    onEnter: () => {
      updateValidity('resolution')
    },
    context: {
      progressStep: 1, // same for isEmailResponse
      mobileHeaderTitle: i18n.value.enterInformation,
      showPeekAttachments: isEmailResponse,
      isGotoValid: () => validity.resolution
    }
  },
  [STEP_MESSAGE_COST_CHECK_ANY]: {
    next: () => {
      if (!isDesktop.value && requestUpdateCosts.value)
        return STEP_MESSAGE_COST_UPDATE
      return isEmailResponse
        ? STEP_DOCUMENTS_OVERVIEW_REDACTED // dot:style=dotted
        : STEP_REDACTION_PICKER
    },
    context: {
      progressStep: 1, // same for isEmailResponse
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: isEmailResponse ? 2 : 5,
      showPeekAttachments: isEmailResponse,
    }
  },
  [STEP_MESSAGE_COST_CHECK_LAST]: {
    next: () => {
      if (!isDesktop.value && requestUpdateCosts.value)
        return STEP_MESSAGE_COST_UPDATE
      return isEmailResponse
        ? STEP_DOCUMENTS_OVERVIEW_REDACTED // dot:style=dotted
        : STEP_REDACTION_PICKER
    },
    context: {
      progressStep: 1, // same for isEmailResponse
      mobileHeaderTitle: i18n.value.enterInformation,
      questionCurrent: isEmailResponse ? 2 : 5,
      showPeekAttachments: isEmailResponse,
      isGotoValid: () => {
        if (isDesktop.value && requestUpdateCosts.value) return validity.costs
        return true
      }
    }
  },
  [STEP_MESSAGE_COST_UPDATE]: {
    next: () => {
      return isEmailResponse
        ? STEP_DOCUMENTS_OVERVIEW_REDACTED // dot:style=dotted
        : STEP_REDACTION_PICKER
    },
    onEnter: () => {
      updateValidity('costs')
    },
    context: {
      isGotoValid: () => validity.costs,
      progressStep: 1, // same for isEmailResponse
      mobileHeaderTitle: i18n.value.enterInformation,
      showPeekAttachments: isEmailResponse,
    }
  },
  [STEP_REDACTION_PICKER]: {
    next: () => {
      if (attachmentsSelectedPdfRedaction.value.length === 0)
        return STEP_DOCUMENTS_OVERVIEW_REDACTED
      return STEP_REDACTION_REDACT // TODO
    },
    onEnter: () => {
      attachments.selectSubset(attachments.redactNudgable)
      pdfRedactionUploaded()
      // TODO is this still correct?
      if (!isEmailResponse) attachments.selectAllNewRedactableAttachments()
    },
    context: {
      // n/a for isEmailResponse
      progressStep: 2,
      mobileHeaderTitle: i18n.value.redact,
    }
  },
  [STEP_REDACTION_REDACT]: {
    next: () => {
      if (
        pdfRedactionCurrentIndex.value <
        attachmentsSelectedPdfRedaction.value.length - 1
      ) {
        return STEP_REDACTION_REDACT
      }
      return isEmailResponse
        ? STEP_MESSAGE_STATUS // dot:style=dotted
        : STEP_DOCUMENTS_OVERVIEW_REDACTED
    },
    context: {
      progressStep: isEmailResponse ? 0 : 2,
      mobileHeaderTitle: i18n.value.redact
    },
    onEnter: () => {
      if (isEmailResponse && attachments.selected.length === 0) {
        attachments.selectSubset(attachments.redactNudgable)
      }
    }
  },
  [STEP_DOCUMENTS_OVERVIEW_REDACTED]: {
    next: STEP_OUTRO,
    onEnter: () => {
      attachments.unselectSubset(attachments.redactable)
      attachmentsOverviewActions.value = false
      pdfRedactionUploaded()
    },
    context: {
      progressStep: isEmailResponse ? 1 : 2,
      mobileHeaderTitle: i18n.value.preview,
    }
  },
  [STEP_OUTRO]: {
    next: STEP_OUTRO,
    onEnter: () => {
      guardBeforeunload(false)
    },
    context: {
      progressStep: isEmailResponse ? 1 : 2,
      mobileHeaderTitle: i18n.value.done
    }
  }
}

const fieldErrorStep = {
  costs: STEP_MESSAGE_COST_UPDATE,
  date: STEP_MESSAGE_DATE,
  registered_mail_date: STEP_MESSAGE_DATE,
  status: STEP_MESSAGE_STATUS,
  resolution: STEP_MESSAGE_STATUS,
  recipient_public_body: STEP_MESSAGE_PUBLICBODY_CHECK,
  sender_public_body: STEP_MESSAGE_PUBLICBODY_CHECK,
  is_response: STEP_MESSAGE_SENT_OR_RECEIVED
}

/* --- state machine, visualization --- */

const stepsConfigVisualize = (c) =>
  'dot -Tpng << eot | display -\n' +
  'digraph "editmessageflow" {\n' +
  Object.keys(c)
    .map((state) => `  "${state}";\n`)
    .join('') +
  Object.keys(c)
    .map((fromState) => {
      const nextSourcecode = c[fromState].next.toString()
      // match all STEP_* with optional "dot edge tag" in a comment, like so:
      // some.code(); return STEP_FOO; // dot:key="attr"
      return [...nextSourcecode.matchAll(/\b(STEP_\w+)(?:.*\/\/.*dot:(.*))?/g)]
        .map(([, toState, dotEdgeTag]) => `  "${fromState}" -> "${toState}" [${dotEdgeTag || ''}];\n`)
        .join('')
      })
    .join('') +
  '}\n' +
  'eot\n'

if (debug.value) console.info(stepsConfigVisualize(stepsConfig))

/* --- state machine, hash-router style ---

// This naive implementation of a hash-router for steps works
// - back button works as intended
// - load into any step, too
// but
// - there are timing issues, i.e. uppyClick doesn't really fire - probably due to nextTick not waiting long enough for the hashchange to settle
// - going history.back arbitrarily breaks state in subtle ways, i.e. when going from STEP_DOCUMENTS_CONVERT_PDF to STEP_DOCUMENTS_SORT
// A better implementation:
// - hash is not "reactively equivalent" to the step
// - instead, on gotoStep, strategically decide whether to pushState or just silently update the internal step
// - this way history.back goes back to certain "checkpoints"
// - only these checkpoints are exposed for arbitrary (re-)entry into the flow
// - it could *maybe* use vue-router

const getStepFromHash = () => {
  const step = parseInt(document.location.hash.substring(1))
  if (!step) {
    console.warn('step not valid')
    return STEP_INTRO
  }
  return step
}
const step = ref(getStepFromHash())
if (step.value !== firstStep) {
  guardBeforeunload(true)
}
gotoStep(step.value)
addEventListener('hashchange', () => {
  step.value = getStepFromHash()
})
*/
</script>

<template>
  <OnlineHelp ref="onlineHelp" />

  <SimpleStepper
    class="sticky-top position-md-static"
    :step="stepContext.progressStep"
    :steps="progressSteps"
  >
    <template v-if="step === STEP_OUTRO">
      <small>{{ i18n.done }}</small>
    </template>
    <template v-else>
      {{ i18n.step }} <strong>{{ stepContext.progressStep + 1 }}/{{ isEmailResponse ? 2 : 3 }}</strong>:
      {{ stepContext.mobileHeaderTitle }}
    </template>
  </SimpleStepper>

  <div class="container">
    <!-- TODO button does not support going back throug pdfRedactionCurrentIndex-->
    <div v-if="step === STEP_INTRO" class="my-3">
      <a class="btn btn-link text-decoration-none ps-0" href="../.."
        >← <u>{{ i18n.cancel }}</u></a
      >
    </div>
    <div v-else-if="![STEP_OUTRO, STEP_INTRO_EMAIL].includes(step)" class="my-3">
      <a @click="backStep" class="btn btn-link text-decoration-none ps-0"
        >← <u>{{ i18n.back }}</u></a
      >
    </div>
  </div>

  <div v-if="error" class="container">
    <div class="alert alert-danger alert-dismissible show" role="alert">
      <h4 class="alert-heading">
        {{ i18n.error || 'Error' }}
      </h4>
      <button type="button" class="btn-close" data-bs-dismiss="alert" :aria-label="i18n.close" @click="error = false" />
      <ul v-if="error?.non_field_errors">
        <li v-for="(errorMessage, errorIndex) in error.non_field_errors" :key="errorIndex">
          {{ errorMessage }}
        </li>
      </ul>
      <dl v-else-if="typeof error === 'object'">
        <template v-for="(value, key) in error" :key="key">
          <dt>{{ key }}</dt>
          <dd>
            {{ value.join?.(', ') || value }}
            <hr/>
            <div v-if="key in fieldErrorStep" class="d-flex gap-1 flex-column flex-sm-row justify-content-sm-end">
              <button
                type="button"
                class="btn btn-primary"
                @click="gotoStep(fieldErrorStep[key])"
                >
                {{ i18n.review }}<!--{{ fieldErrorStep[key] }}-->
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                @click="gotoStep(STEP_DOCUMENTS_OVERVIEW_REDACTED)"
                >
                {{ i18n.backToSubmit }}
              </button>
            </div>
          </dd>
        </template>
      </dl>
      <div v-if="Object.keys(error).length === 0 || typeof error === 'string'">
        <pre>{{ error }}</pre>
      </div>
    </div>
  </div>

  <details v-if="debug" class="container">
    <summary class="DEBUG">DEBUG</summary>
    <div>isEmailResponse={{ isEmailResponse }}</div>
    <div>step={{ step }}</div>
    <div>history={{ stepHistory.join(' ') }}</div>
    <div>stepContext={{ stepContext }}</div>
    <div>isGotoValid={{ isGotoValid }}</div>
    <div>values={{ values }}</div>
    <div>
      attachments.autoApproveSelection={{ attachments.autoApproveSelection }}
    </div>
    <span>
      <!-- eslint-disable-next-line vue/no-mutating-props -->
      <button type="button" @click="user_is_staff = !user_is_staff">
        {{ user_is_staff ? '☑' : '☐' }} staff
      </button>
    </span>
    <span>isDesktop={{ isDesktop }}</span>
    <button class="btn btn-secondary btn-sm" type="button" @click="approveAndPublish"
      style="font-size: 50%; margin-left: 1em">
      approveAndSubmit()
    </button>
    <button class="btn btn-secondary btn-sm" type="button" @click="requestAndMessageUpdateValues"
      style="font-size: 50%; margin-left: 1em">
      submitFetch()
    </button>
    <!--<pre>{{ validity }}</pre>-->
    <!-- <span v-if="debug" class="debug">desktop={{ isDesktop }},</span> -->
    <!--<span class="debug">{{ stepHistory.join(',') }}</span>-->
    <!--<span class="debug">p{{ progress }}</span>-->
    <!--<small>{{ { uiDocuments, uiDocumentsUpload } }}</small>-->
    <!--<span class="debug">{{ values.isYellow }}</span>-->
    <!--<span class="debug">{{ isGotoValid }}</span>-->
    <!--<span class="debug">{{documentsSelectedPdfRedaction}}</span>-->
    <!--<span class="debug">documentsSelectedPdfRedaction={{ documentsSelectedPdfRedaction.map(d => d.id).join(',') }}</span>-->
  </details>

  <div class="step-container">
    <div v-show="step === STEP_INTRO" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-12 d-flex flex-column">
          <div class="row mt-3 mb-5 justify-content-center order-md-2">
            <div class="col-md-6 order-3 order-md-1"
              :class="{
                'col-md-6': showMobileAppContent,
                'col-md-12': !showMobileAppContent
              }"
              >
              <div v-if="showMobileAppContent" class="mt-3 mb-1 mb-md-3">
                {{ i18n.uploadFilesAddendum }}:
              </div>
              <button
                type="button"
                @click="fileUploader.clickFilepick() || (fileUploaderShow = true)"
                v-if="!isDesktop && !fileUploaderShow"
                class="btn btn-outline-primary btn-lg d-block w-100 mb-3"
              >
                <i class="fa fa-upload fa-2x"></i><br />
                {{ i18n.uploadFiles }}
              </button>
              <div class="d-flex gap-3 row">
                <!-- on mobile, show the table first so websocket triggers a nice pop-in -->
                <FileUploader
                  :config="config"
                  :allowed-file-types="config.settings.allowed_filetypes"
                  :auto-proceed="true"
                  :show-uppy="fileUploaderShow"
                  ref="fileUploader"
                  @uploading="fileUploaderUpload"
                  @upload-success="fileUploaderSucceeded"
                  @upload-complete="fileUploaderCompleted"
                  class="order-2 order-md-1"
                  :class="{
                    'col-md-6': !showMobileAppContent,
                    'col-12': showMobileAppContent
                    }"
                  />
                <div class="col order-1 order-md-2"
                  :class="{
                    'col-md-6': !showMobileAppContent,
                    'col-12': showMobileAppContent
                  }"
                  >
                  <AttachmentsTable
                    v-if="attachments.all.length > 0"
                    :subset="attachments.all"
                    badges-type action-delete
                    dense
                    >
                    <template #before-cards>
                      <div v-if="isDesktop && !fileUploaderShow" class="text-end">
                        <button
                          type="button" class="btn btn-sm btn-link"
                          @click="fileUploaderShow = true"
                          >{{ i18n.addMoreFiles }}</button>
                      </div>
                    </template>
                    <template #before-table>
                      <div v-if="isDesktop && !fileUploaderShow" class="text-end">
                        <button
                          type="button" class="btn btn-sm btn-link"
                          @click="fileUploaderShow = true"
                          >{{ i18n.addMoreFiles }}</button>
                      </div>
                    </template>
                  </AttachmentsTable>
                </div>
              </div>
            </div>
            <div v-if="showMobileAppContent" class="d-none d-md-block col-md-1 order-2">
              <div class="fw-bold text-center text-uppercase" style="margin-top: 10em">oder</div>
            </div>
            <div v-if="showMobileAppContent" class="col-md-5 order-1 order-md-3">
              <div class="mt-3 mb-1 mb-md-3">
                {{ i18n.scanDocumentsAddendum }}:
              </div>
              <div class="row py-md-3" v-if="mobileAppContent !== null">
                <div class="col-lg-6 mb-5">
                  <div v-html="mobileAppContent"></div>
                </div>
                <div class="col-lg-6 d-none d-md-block">
                  <div v-html="i18n._('scanDocumentsInstructions', { url: config.url.mobileAppInstall })"></div>
                </div>
              </div>
              <div v-else>
                <div class="spinner-border" role="status">
                  <span class="visually-hidden">{{ i18n.loading }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="alert alert-warning order-md-1">
            <h4><i class="fa fa-lightbulb-o fa-lg"></i> {{ i18n.hint }}</h4>
            <p v-html="i18n.redactLaterHint1"></p>
            <p v-html="i18n.redactLaterHint2"></p>
          </div>
          <div class="alert alert-warning order-md-3">
            <h4>
              <i class="fa fa-exclamation-circle fa-lg"></i>
              {{ i18n.new }}
            </h4>
            <p>
              {{ i18n.newWarning }}
            </p>
            <p
              v-html="
                i18n._('newLinkOldFlow', { url: config.url.legacyPostupload })
              "
            ></p>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_INTRO_EMAIL" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="row my-5 justify-content-center">
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
              <div>
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
              </div>
              <div class="d-print-none alpha-message__toolbar alpha-message__toolbar--sticky alpha-message__toolbar--stickybump">
                <div class="alpha-message__wrap d-flex flex-column flex-sm-row flex-wrap justify-content-between py-2">
                  <!-- Problem button -->
                  <DjangoSlot name="test_problembutton"></DjangoSlot>
                  <!-- no need for Edit button, because never can_edit email message -->
                  <!-- Redact button -->
                  <!-- the button will trigger the modal+form rendered outside of Vue component -->
                  <DjangoSlot name="redactbutton"></DjangoSlot>
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
    <div v-show="step === STEP_DOCUMENTS_CONVERT" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9 fw-bold">
          {{ i18n.documentsConvertIrrelevant }}
        </div>
        <div class="my-3">
          <!-- note: convertable subset misses those that have been converted-created in this very step -->
          <AttachmentsTable
            :subset="attachments.convertable"
            actions action-delete selection-action-delete badges-type
            />
        </div>
        <!-- irrelevant attachments re-appear after a refresh;
           should they be (were they?) permantly marked "processed" or deleted?
           "fresh" images have can_delete=true (among other unrelated props)
           "converted" images don't...
           not sure if there is a good distinction/semantics here.
           -->
        <ImagesConverter
          @converted="() => { if (attachments.convertable.length === 0) gotoStep() }"
          />
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_SORT" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9 fw-bold">
          {{ i18n.documentsDragOrder }}
        </div>
        <ImageDocumentPagesSortable :idx="0" show-rotate />
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_CONVERT_PDF" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="text-center my-3">
            <i class="fa fa-file-image-o fa-4x"></i>
            <i class="fa fa-arrow-right fa-2x"></i>
            <i class="fa fa-file-pdf-o fa-4x"></i>
          </div>
        </div>
        <div class="text-center fw-bold my-3">
          {{ i18n.documentsFromImages }}
        </div>
        <div
          v-if="attachments.images[0]"
          class="documents-filename p-2 my-3 mx-auto"
        >
          <div class="form-group">
            <input
              id="documents_filename"
              v-model="attachments.images[0].name"
              class="form-control"
            />
            <label for="documents_filename">
              {{ i18n.changeFilename }}
            </label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="fw-bold">
            {{ i18n.documentsAvailable }}
          </div>
          <AttachmentsTable :subset="attachments.redactable" action-delete cards-bg-transparent :as-card-threshold="0" />
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_SENT_OR_RECEIVED" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <label class="fw-bold form-label">
            {{ i18n.letterSentOrReceived }}
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in messageIsResponseChoices" :key="choiceIndex">
            <input type="radio" name="sent" v-model="values.is_response" required="" class="form-check-input"
              :id="'id_sent_' + choiceIndex" :value="choice.value" />
            <label class="form-check-label" :for="'id_sent_' + choiceIndex">{{
              choice.label
            }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_PUBLICBODY_CHECK" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="!values.is_response">
              {{ i18n.messagePublicbodyCheckTo }}
            </template>
            <template v-else>
              {{ i18n.messagePublicbodyCheckFrom }}
            </template>
          </label>
          <div style="margin: 1em 0; font-style: italic">
            {{ props.foirequest.public_body.name }}
          </div>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { value: true, label: i18n.yes },
            { value: false, label: i18n.noDifferentPublicBody }
          ]" :key="choiceIndex">
            <input type="radio" required="" class="form-check-input" v-model="messagePublicBodyIsDefault"
              :id="'id_pbisdefault_' + choiceIndex" :value="choice.value" />
            <label class="form-check-label" :for="'id_pbisdefault_' + choiceIndex">{{ choice.label }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_PUBLICBODY_UPDATE ||
      (isDesktop &&
        step === STEP_MESSAGE_PUBLICBODY_CHECK &&
        !messagePublicBodyIsDefault)
      " class="container">
      <!-- appears "indented" on md=isDesktop viewport -->
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="values.is_response">
              {{ i18n.messagePublicbodyUpdateTo }}
            </template>
            <template v-else>
              {{ i18n.messagePublicbodyUpdateFrom }}
            </template>
          </label>
          <!-- TODO list-view=resultList has no pagination, but betaList doesnt work yet? -->
          <PublicbodyChooser v-if="!messagePublicBodyIsDefault" :search-collapsed="false" scope="editmessageflow_publicbody"
            name="publicbody" :config="config" :value="props.foirequest.public_body.id" list-view="resultList"
            :show-filters="false" :show-badges="false" :show-found-count-if-idle="false"
            @update="updateValuePublicBody"
            />
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_DATE" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <label class="fw-bold form-label field-required" for="id_date">
            {{ i18n.messageDate }}
          </label>
          <!-- has to be @required "one too early" so checkValidity doesn't return true when empty on enter step -->
          <!-- TODO "always" required might break early post/submit
                :required="step === STEP_MESSAGE_DATE || step === STEP_MESSAGE_PUBLICBODY_CHECK"
                maybe: step > STEP_MESSAGE_PUBLICBODY_CHECK ?
              -->
          <input id="id_date" class="form-control" type="date" name="date" v-model="values.date" :class="{
            'is-invalid': validity.date === false,
            'is-valid': validity.date === true
          }" required :min="props.date_min" :max="props.date_max" @input="updateValidity('date')" />
          <div class="form-check">
            <input
              class="form-check-input"
              type="checkbox"
              v-model="values.is_registered_mail"
              id="id_is_registered_mail"
            />
            <label class="form-check-label" for="id_is_registered_mail">
              {{ i18n.messageIsRegisteredMail }}
              <span
                type="button"
                v-bs-tooltip
                tabindex="0"
                data-bs-toggle="tooltip"
                data-bs-placement="bottom"
                :title="i18n.messageRegisteredMailInfo"
              >
                <i class="fa fa-info-circle"></i>
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
    <div
      v-show="
        step === STEP_MESSAGE_DATE_REGISTERED_MAIL ||
        (isDesktop && step === STEP_MESSAGE_DATE && values.is_registered_mail)
      "
      class="container"
    >
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label
            class="fw-bold form-label field-required"
            for="id_registered_mail"
          >
            {{ i18n.messageDateRegisteredMail }}
          </label>
          <!-- TODO set min/max? -->
          <input
            type="date"
            class="form-control"
            id="id_registered_mail_date"
            name="registered_mail_date"
            :required="values.is_registered_mail"
            @input="updateValidity('registered_mail_date')"
            v-model="values.registered_mail_date"
          />
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_STATUS" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="values.is_response && requestWasResolved">
              {{ i18n.messageStatusIsResolvedAfterReceivedStill }}
            </template>
            <template v-if="values.is_response && !requestWasResolved">
              {{ i18n.messageStatusIsResolvedAfterReceived }}
            </template>
            <template v-if="!values.is_response && requestWasResolved">
              {{ i18n.messageStatusIsResolvedAfterSentStill }}
            </template>
            <template v-if="!values.is_response && !requestWasResolved">
              {{ i18n.messageStatusIsResolvedAfterSent }}
            </template>
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in schemas.status_choices"
            :key="choice.value">
            <input type="radio" name="status" required="" class="form-check-input"
              :class="{ 'is-invalid': choice.errors }" :id="'id_status_' + choiceIndex" v-model="values.status"
              :value="choice.value" @input="updateValidity('status')" />
            <label class="form-check-label" :for="'id_status_' + choiceIndex">
              <template v-if="requestWasResolved">
                <template v-if="choice.value === 'resolved'">
                  {{ i18n.messageStatusIsResolvedStill }}
                </template>
                <template v-else>
                  {{ i18n.messageStatusIsResolvedNotAgain }}
                </template>
              </template>
              <template v-else>
                <template v-if="choice.value === 'resolved'">
                  {{ i18n.messageStatusIsResolved }}
                </template>
                <template v-else>
                  {{ i18n.messageStatusIsResolvedNot }}
                </template>
              </template>
            </label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_MESSAGE_RESOLUTION ||
      (isDesktop && step === STEP_MESSAGE_STATUS && requestIsResolved)
      " class="container">
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold col-form-label" for="id_resolution">
            {{ i18n.messageResolution }}
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in requestResolutionChoices" :key="choice.value">
            <input type="radio" name="resolution" :required="requestIsResolved" class="form-check-input"
              v-model="values.resolution"
              :id="'id_resolution_' + choiceIndex" :value="choice.value"
              @input="updateValidity('resolution')"
              />
            <label class="form-check-label" :for="'id_resolution_' + choiceIndex">{{ choice.label }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_COST_CHECK_ANY" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <label class="fw-bold col-form-label">
            {{ i18n.messageCostCheck }}
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { label: i18n.no, value: false },
            { label: i18n.yes, value: true }
          ]" :key="choiceIndex">
            <input type="radio" required="" class="form-check-input" v-model="requestUpdateCosts"
              :id="'id_nowcost_' + choiceIndex" :value="choice.value"
              @input="updateValidity('costs')"
              />
            <label class="form-check-label" :for="'id_nowcost_' + choiceIndex">{{ choice.label }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_COST_CHECK_LAST" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">{{ i18n._('questionOf', { current: stepContext.questionCurrent, total: questionTotal }) }}</div>
          <!-- TODO: i18n: in DE, the amount format is not l10n: 1.00 instead of 1,00
            also, API returns floats, so this actually should be decimalized i18n-awarely...
            (or provided as a formatted string by the API)
            also, the order of "number currency" is currently hardcoded here
           -->
          <label
            class="fw-bold col-form-label"
            for="id_nowcost"
            v-html="i18n._('messageCostCheckLast', { amount: `${requestOldCosts}&nbsp;${currency}` })"
            ></label>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { label: i18n.yes, value: false },
            { label: i18n.no, value: true }
          ]" :key="choiceIndex">
            <input type="radio" required="" class="form-check-input" v-model="requestUpdateCosts"
              :id="'id_nowcost_' + choiceIndex" :value="choice.value"
              @input="updateValidity('costs')"
              />
            <label class="form-check-label" :for="'id_nowcost_' + choiceIndex">{{ choice.label }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_COST_UPDATE ||
      (isDesktop &&
        (step === STEP_MESSAGE_COST_CHECK_ANY ||
          step === STEP_MESSAGE_COST_CHECK_LAST) &&
        requestUpdateCosts)
      " class="container">
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold col-form-label" for="id_costs">
            {{ i18n.messageCost }}
          </label>
          <div class="col-md-8">
            <div class="input-group" style="width: 10rem">
              <!-- type=number does not support pattern -->
              <input
                type="number"
                name="costs"
                id="id_costs"
                class="form-control col-3"
                inputmode="decimal"
                style="appearance: textfield; text-align: right"
                min="0"
                max="1000000000"
                step="0.01"
                v-model="values.costs"
                @input="updateValidity('costs')"
                :class="{
                  'is-invalid': validity.costs === false,
                  'is-valid': validity.costs === true
                }" />
              <span class="input-group-text">{{ currency }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_REDACTION_PICKER" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <label class="fw-bold col-form-label">
            {{ i18n.redactionPick }}
          </label>
          <p>
            {{ i18n.redactionInfo }}
          </p>
          <AttachmentsTable :subset="attachments.redactable" table-selection selection-buttons :as-card-threshold="0">
            <template #after-row="slotProps" v-if="pickNotAutoApprove">
              <label
                class="d-flex flex-column position-absolute position-md-static top-0 end-0 py-3 px-1"
              >
                <!-- like v-model, but default true -->
                <input
                  v-if="!slotProps.attachment.approved"
                  type="checkbox"
                  :checked="
                    attachments.autoApproveSelection[
                      slotProps.attachment.id
                    ] !== false
                  "
                  @input="
                    (evt) => {
                      attachments.autoApproveSelection[
                        slotProps.attachment.id
                      ] = evt.target.checked
                    }
                  "
                />
                <input
                  v-else
                  type="checkbox"
                  checked
                  disabled
                  v-bs-tooltip
                  data-bs-toggle="tooltip"
                  data-bs-placement="top"
                  :title="i18n.alreadyPublished"
                />
              </label>
            </template>
            <template #after-card="slotProps" v-if="pickNotAutoApprove">
              <label v-if="!slotProps.attachment.approved" class="text-center">
                <input
                  type="checkbox"
                  :checked="
                    attachments.autoApproveSelection[
                      slotProps.attachment.id
                    ] !== false
                  "
                  @input="
                    (evt) => {
                      attachments.autoApproveSelection[
                        slotProps.attachment.id
                      ] = evt.target.checked
                    }
                  "
                />
                {{ i18n.publish }}*
              </label>
              <div v-else>
                {{ i18n.alreadyPublished }}
              </div>
            </template>
            <template #after-table v-if="pickNotAutoApprove">
              <div class="text-end px-2">
                {{ i18n.documentsApproveLater }}
                <span class="fa fa-level-up" aria-hidden="true"></span>
              </div>
            </template>
            <template #after-cards v-if="pickNotAutoApprove">
              <div class="text-end px-2">
                * {{ i18n.documentsApproveLater }}
              </div>
            </template>
          </AttachmentsTable>
          <div
            v-if="props.user_is_staff && props.foirequest.public && !pickNotAutoApprove"
            class="alert alert-secondary text-center my-3"
            role="alert"
            >
            <p>
              {{ i18n.publicRequestApproveHint }}
            </p>
            <button
              type="button"
              role="button"
              :aria-disabled="pickNotAutoApprove ? 'true' : 'false'"
              class="btn btn-primary"
              :class="{ disabled: pickNotAutoApprove }"
              @click="pickNotAutoApprove = true"
              >
              {{ i18n.publicRequestPickNotAutoApprove }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_REDACTION_REDACT">
      <div class="container">
        <div class="row">
          <div class="col">
            <label class="fw-bold col-form-label">
              {{
                i18n._('redactionCounter', {
                  current: pdfRedactionCurrentIndex + 1,
                  total: attachmentsSelectedPdfRedaction.length
                })
              }},
              {{ pdfRedactionCurrentDoc?.name }}
            </label>
            <div class="row">
              <!-- no need to import vBsCollapsePersistent,
                snippets/bootstrap DOMContentLoaded will just work -->
              <DjangoSlot name="redaction_explanation"></DjangoSlot>
            </div>
            <div class="mt-2 mb-3">
              <button
                type="button"
                class="btn btn-link text-decoration-underline"
                @click="onlineHelp.show(config.url.helpPostuploadRedaction)"
              >
                {{ i18n.helpNeeded }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div>
        <div class="debug" v-if="debug">
          DEBUG: pdfRedactionCurrentIndex= {{ pdfRedactionCurrentIndex }}
        </div>
        <PdfRedaction
          class="pdf-redaction-tool"
          v-if="pdfRedactionCurrentDoc"
          :key="pdfRedactionCurrentDoc.id"
          :pdf-path="pdfRedactionCurrentDoc.file_url"
          :attachment-id="pdfRedactionCurrentDoc.id"
          :attachment-url="pdfRedactionCurrentDoc.anchor_url"
          :auto-approve="
            attachments.autoApproveSelection[pdfRedactionCurrentDoc.id] !==
            false
          "
          :post-url="
            config.url.redactAttachment.replace(
              '/0/',
              '/' + pdfRedactionCurrentDoc.id + '/'
            )
          "
          :hide-done-button="true"
          :bottom-toolbar="false"
          :no-redirect="true"
          :redact-regex="['teststraße\ 1']"
          :can-publish="true"
          :config="config"
          @uploaded="pdfRedactionUploaded"
          @hasredactionsupdate="pdfRedactionCurrentHasRedactions = $event"
          ref="pdfRedaction"
        >
          <!--
              <template #toolbar-right>
                <div class="btn-group" v-show="isDesktop">
                  <button
                    type="button"
                    class="btn btn-primary"
                    @click="pdfRedactionRedact()"
                    :disabled="pdfRedactionProcessing">
                    <i
                      v-show="!pdfRedactionProcessing"
                      class="fa fa-thumbs-o-up"></i>
                    <span
                      class="spinner-border spinner-border-sm"
                      v-show="pdfRedactionProcessing"
                      role="status"
                      aria-hidden="true" />
                    Ich bin fertig mit Schwärzen
                  </button>
                </div>
              </template>
              -->
        </PdfRedaction>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW_REDACTED" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="fw-bold col-form-label">
            {{ i18n.documentsOverview }}
          </div>
          <AttachmentsTable
            :subset="attachments.relevant.filter(att => !att.redacted && !att.is_image)"
            badges-redaction badges-resolution
            :actions="attachmentsOverviewActions"
          >
            <template #before-cards>
              <div class="text-end mb-2">
                <button
                  type="button"
                  class="btn btn-link"
                  @click="
                    () =>
                      (attachmentsOverviewActions = !attachmentsOverviewActions)
                  "
                >
                  {{ attachmentsOverviewActions ? i18n.done : i18n.edit }}
                </button>
              </div>
            </template>
            <template #before-table> </template>
          </AttachmentsTable>
        </div>
      </div>
      <!-- filter hides unredacted attachments that have a redaction version -->
    </div>
    <div v-show="step === STEP_OUTRO" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9 text-center">
          <div class="my-3">
            <i class="fa fa-check-square fa-4x"></i>
          </div>
          <div class="fw-bold col-form-label">
            {{ i18n.documentsAddedSuccessfully }}
          </div>
          <div>
            {{ i18n.requestUpdatedThanks }}
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW || step === STEP_DOCUMENTS_SORT" class="container">
      <div class="row justify-content-center">
        <div class="col-sm-9 col-md-6 mt-3">
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100"
            @click="gotoStep(STEP_INTRO)"
          >
            <i class="fa fa-plus"></i>
            {{ i18n.uploadOrScanMoreFiles }}
          </button>
        </div>
      </div>
    </div>
    <div class="container my-3" v-if="stepContext.showPeekAttachments && (attachments.all.length > 0)">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <button
            type="button"
            class="btn btn-link ps-0"
            data-bs-toggle="collapse"
            data-bs-target="#editmessageflowPeekAttachments"
            aria-expanded="false"
            aria-controls="editmessageflowPeekAttachments">
            {{ i18n.pleasePeek }}
          </button>
          <div id="editmessageflowPeekAttachments" class="collapse bg-body-tertiary p-3">
            {{ i18n.clickIconsForPreview }}
            <AttachmentsTable
              :subset="attachments.all"
              badges-type
              dense
              preview-hide-info-sidebar
              as-table-only
              >
            </AttachmentsTable>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="sticky-bottom mt-auto mt-md-0 bg-body py-2">
    <div class="container">
      <div class="row justify-content-center">
        <div class="col-md-9 col-lg-6 text-center">
          <template v-if="step === STEP_REDACTION_REDACT">
            <button
              type="button"
              @click="pdfRedactionRedact()"
              class="btn btn-primary d-block w-100"
              :disabled="pdfRedactionProcessing"
            >
              <span
                class="spinner-border spinner-border-sm"
                v-show="pdfRedactionProcessing"
                role="status"
                aria-hidden="true"
              />
              {{ i18n.redactionDone }}
            </button>
            <div class="mt-2">
              <small>
                {{ i18n.redactionCheck }}
              </small>
              <div v-if="debug" class="debug">
                DEBUG: hasRedactions={{ pdfRedactionCurrentHasRedactions }}
              </div>
            </div>
          </template>
          <template v-else-if="step === STEP_DOCUMENTS_OVERVIEW_REDACTED">
            <button
              type="button"
              @click="approveAndPublish"
              class="btn btn-primary d-block w-100"
              :disabled="isSubmitting"
            >
              <span
                class="spinner-border spinner-border-sm"
                v-show="isSubmitting"
                role="status"
                aria-hidden="true"
              />
              {{ i18n.confirm }}
            </button>
            <div class="mt-2" v-if="!foirequest.public">
              <small>
                {{ i18n.requestNonPublicHint }}
              </small>
            </div>
          </template>
          <template v-else-if="step === STEP_OUTRO">
            <a :href="props.foirequest.url" class="btn btn-primary d-block w-100">
              {{ i18n.requestShow }}
            </a>
          </template>
          <template v-else-if="step === STEP_INTRO">
            <!-- should be blank -->
            <button
              v-if="debug"
              type="button"
              @click="gotoStep()"
              class="action btn btn-outline-primary btn-sm mt-1"
            >
              DEBUG skip
            </button>
            <button
              v-if="fileUploaderShow || attachments.all.length > 0 || attachments.images.length > 0"
              type="button" class="btn btn-primary d-block w-100"
              :disabled="fileUploaderUploading || (attachments.all.length === 0 && attachments.images.length === 0)"
              @click="gotoStep()"
              >
              {{ i18n.next }}
            </button>
            <div class="mt-2">
              <small>
                {{ i18n.notYetPublishedHint }}
              </small>
            </div>
          </template>
          <template v-else-if="step === STEP_INTRO_EMAIL">
            <button
              type="button"
              @click="gotoStep()"
              class="btn btn-primary d-block w-100"
            >
              <template v-if="attachments.convertable.length === 0 && attachments.redactNudgable.length === 0">
                {{ i18n.next }}
              </template>
              <template v-else>
                {{ i18n.readAndRedactAttachments }}
              </template>
            </button>
            <div class="mt-2" v-if="attachments.convertable.length > 0">
              <small>
                {{ i18n.imageAttachments }}
                {{ i18n.nextStepConvertImages }}
              </small>
            </div>
          </template>
          <template v-else-if="step === STEP_DOCUMENTS_SORT">
            <button
              type="button"
              @click="gotoStep()"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.doneSorting }}
            </button>
          </template>
          <template v-else-if="step === STEP_DOCUMENTS_CONVERT_PDF">
            <button
              v-if="attachments.images.length > 0"
              type="button"
              @click="attachmentsConvertImages"
              class="btn btn-primary d-block w-100"
              :disabled="attachmentsImagesConverting"
            >
              <span
                class="spinner-border spinner-border-sm"
                v-if="attachmentsImagesConverting"
                role="status"
                aria-hidden="true"
              />
              {{ i18n.createPdf }}
            </button>
            <button
              v-else
              type="button"
              @click="gotoStep()"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.next }}
            </button>
          </template>
          <template v-else-if="step === STEP_MESSAGE_DATE">
            <button
              type="button"
              :disabled="!isGotoValid"
              @click="gotoStep()"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.next }}
            </button>
            <button
              v-if="debug"
              type="button"
              @click="debugSkipDate"
              class="btn btn-outline-primary btn-sm mt-1 d-block w-100"
            >
              DEBUG set today
            </button>
          </template>
          <template v-else>
            <button
              type="button"
              @click="gotoStep()"
              :disabled="!isGotoValid"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.next }}
            </button>
          </template>
        </div>
        <!--/.col-lg-9-->
      </div>
      <!--/.row-->
    </div>
    <!--/.container-->
  </div>
  <!--/.sticky-bottom-->
</template>

<style lang="scss" scoped>
@use 'sass:map';
@import 'bootstrap/scss/functions';
@import '../../../styles/variables.scss';

@include media-breakpoint-up(xl) {
  .step-container {
    min-height: 48rem; // so that buttons are always at the same position
  }
}

.debug {
  opacity: 0.5 !important;
  color: #888 !important;

  &.btn {
    color: black !important;
  }
}

/* make form-check more accessible; whole block is padded + clickable */

.form-check {
  background-color: var(--bs-tertiary-bg);
  padding: 0;
  margin-top: 0.5em;
  margin-bottom: 0.5em;

  &:hover {
    background-color: var(--bs-secondary-bg);
  }
}

.form-check label {
  padding: 1em 1em 1em 2.5em;
  display: block;
}

.form-check-input {
  margin-top: 1.25em;
  margin-left: 0.75em;
  border-color: var(--bs-body-color);
  border-width: 2px;

  .form-check:hover & {
    border-color: var(--bs-primary);
  }

  &:checked {
    background-color: black;
  }
}

/* re-style the component's filename-dialog so first it looks less interactive,
 * until you click "change filename" */

.documents-filename {
  max-width: 20em;
  --bs-link-color-as-light-bg: #0047e120;
  background-color: var(--bs-link-color-as-light-bg);

  input {
    font-weight: bolder;
  }

  /* "hide" that this is a regular, editable Bootstrap input... */
  input:not(:focus) {
    background: transparent;
    border-color: transparent;
    box-shadow: none;
  }

  /* ...until its label (looking like a link-button) is clicked, which gives it focus */
  label {
    cursor: pointer;
    text-decoration: underline;
    color: var(--bs-link-color);
    /* padding-left matches bootstrap's form-group>input for indent */
    padding: 0.25rem 0.25rem 0.25rem 0.75rem;
  }
}

/* respect simple-stepper's height when sticky */

@include media-breakpoint-down(md) {
  .pdf-redaction-tool :deep(.sticky-top) {
    top: 41px; // height of .simple-stepper/breadcrumbs
  }
}

/* email */

.email-subject {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.email-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

</style>
