<script setup>
import { computed, defineProps, onMounted, provide, reactive, ref } from 'vue'
import DjangoSlot from '../../lib/django-slot.vue'
import SimpleStepper from './simple-stepper.vue'
// import PublicbodyChooser from '../publicbody/publicbody-chooser'
import PublicbodyChooser from '../publicbody/publicbody-beta-chooser'
// TODO linter wrong? the two above are just fine...
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import PdfRedaction from '../redaction/pdf-redaction.vue'
import { messageRetrieve, messagePartialUpdate, messagePublishCreate } from '../../api/index.ts'
import { useI18n } from '../../lib/i18n'
import { guardBeforeunload, scrollNavIntoViewIfNecessary } from '../../lib/misc'
import { vBsTooltip } from '../../lib/vue-bootstrap'
import { useIsDesktop } from '../../lib/vue-helpers-layout'
import Room from '../../lib/websocket.ts'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import OnlineHelp from '../online-help.vue'

import { requestRetrieve, requestPartialUpdate } from '../../api/index.ts'

import { useAttachments } from '../docupload/lib/attachments'

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import ImageDocumentPagesSortable from '../docupload/image-document-pages-sortable.vue'
import AttachmentsTable from '../docupload/attachments-table.vue'

const props = defineProps({
  config: Object,
  message: Object,
  form: Object,
  schemas: Object,
  // foirequest: Object,
  foirequest_id: String,
  foirequest_apiurl: String,
  foirequest_public_body: Object,
  object_public: Boolean,
  date_min: String,
  date_max: String,
  user_is_staff: Boolean
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
  approveAllUnredactedAttachments
} = useAttachments({
  message: props.message,
  urls: {
    ...props.config.url,
    ...props.config.urls,
    getAttachment: props.config.url.getAttachment.replace('/0/', '/') +
      '?belongs_to=' +
      props.message.id,
  },
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  i18n,
})

// const refreshAttachments = () => {
//   fetchAttachments(draft.value.id)
// }

const { isDesktop } = useIsDesktop()

/* --- debug --- */

const debug = ref(!!localStorage.getItem('fds-postupload-debug'))
window.FDSdebug = (val) => {
  debug.value = typeof val === 'boolean' ? val : !debug.value
  localStorage.setItem('fds-postupload-debug', debug.value ? 'yes' : '')
}

const debugSkipDate = () => {
  values.date = document.forms.postupload.elements.date.max
  values.registered_mail_date = document.forms.postupload.elements.date.max
  updateValidity('date')
  updateValidity('registered_mail_date')
  gotoStep()
}

const draft = ref({})

const error = ref(false)

/*
const createOrRetrieveLastDraft = async () => {
  const requestParam = { query: { request: props.foirequest_id } }
  try {
    const drafts = await messageDraftList({ ...requestParam, throwOnError: true })
    if (drafts.data.objects.length) {
      // TODO: this is not the "newest"
      //   would have to get last page (or increase limit)
      //   either "while drafts.meta.next"
      //   or { limit: 1, offset: results.meta.total_count - 1 }
      draft.value = drafts.data.objects[drafts.data.objects.length - 1]
      // unnecessary, we already get all data from listFoi…
      //   await retrieveFoiMessageDraft({ path: { id: newestDraft.resource_uri }})
    } else {
      draft.value = await messageDraftCreate({
        body: requestParam,
        throwOnError: true
        // body.timestamp: ...
      })
    }
    formSent.value = draft.value.sent
    values.sent = draft.value.sent
    refreshAttachments()
    //  draft.value = r
    //  formSent.value = r.is_response
    //  formStatus.value = r.status
    //  formStatusWasResolved.value = r.status === 'resolved'
  } catch (e) {
    error.value = e.message
  }
}
*/

const values = reactive({})

const requestOldCosts = ref()
const requestHadCosts = ref()
const requestIsResolved = computed(() => values.status === 'resolved')
const requestWasResolved = ref()
const requestUpdateCosts = ref(false)

const retrieveValues = async () => {
  // TODO handle errors
  const { data: request } = await requestRetrieve({
    path: { id: props.foirequest_id },
    throwOnError: true
  })
  values.status = request.status
  values.public_body = request.public_body.resource_uri
  requestOldCosts.value = request.costs
  requestHadCosts.value = parseFloat(request.costs) > 0
  values.costs = request.costs // string "12.34"!
  // TODO get value from schema?
  // requestIsResolved.value = request.status === 'resolved'
  values.resolution = request.resolution
  requestWasResolved.value = request.status === 'resolved'
  const { data: message } = await messageRetrieve({
    path: { id: props.message.id },
    throwOnError: true
  })
  values.is_response = message.is_response
  values.date = ymdifyDate(message.timestamp)
  values.registered_mail_date = message.registered_mail_date
    ? ymdifyDate(message.registered_mail_date)
    : ''
  values.sender_public_body = message.sender_public_body
  values.recipient_public_body = message.recipient_public_body
}

retrieveValues()
  .catch((err) => {
    console.error('retrieveValues error', err)
    error.value = err
  })

const updatePublicBody = (pbUpdateEvt) => {
  // form some reasone, this didn't work inline in the handler
  values.public_body = pbUpdateEvt.resourceUri
}

/*
const updateValue = async (key) => {
  return messagePartialUpdate({
    path: { id: draft.value.id },
    body: { [key]: values[key] },
    throwOnError: true
  })
    .then((r) => {
      draft.value = r.data
    })
    .catch((e) => {
      error.value = e
      return false
    })
}
*/

/* Mobile App Content */

const mobileAppContent = ref(null)
if (props.config.url.mobileAppContent) {
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
  const room = new Room(props.config.url.messageWebsocket)
  room.connect().on('attachment_added', (data) => {
    // When a new attachment is added, refresh the attachments store
    // TODO: can this be a race condition vs. "just added attachment via web ui",
    // which also triggers a websocket event, that can arrive before "the id is present"?
    refreshAttachmentsIfIdNotPresent(data.attachment).then((refreshed) => {
      if (!refreshed) {
        return
      }
      if (step.value === STEP_INTRO) {
        gotoStep(STEP_DOCUMENTS_OVERVIEW)
      }
    })
  })
}

/* --- form handling --- */

/* untangle ambiguous semantics:
 * there is message.sent, but this is not the same.
 * sent in the Form's context means "negated is_response"
 * TODO: this should be cleaned up at the model level.
 */
// const formSent = ref(props.message?.is_response ? '0' : '1')
// const formIsSent = computed(() => formSent.value === '1')

const messagePublicBodyIsDefault = ref(true)

// remove nonsensical combos
const requestResolutionChoices = computed(() => {
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

/* --- form handling, validity --- */

const validity = reactive({
  date: false,
  registered_mail_date: false,
  status: false
})

// TODO updateValidity should (maybe) be called on gotoStep(STEP_MESSAGE_DATE), too
const updateValidity = (key) => {
  let el =
    key === 'form'
      ? document.forms.postupload
      : document.forms.postupload.elements[key]
  // checkValidity is same for any radio button of a given name, we pick the first
  if (el instanceof RadioNodeList) el = el[0]
  // just assume true if browser doesn't support checkValidity
  validity[key] = 'checkValidity' in el ? el.checkValidity() : true
  if (debug.value) {
    if (key === 'form' && !el.checkValidity()) {
      console.log(
        'updateValidity form failed, offending elements:',
        [...document.forms.postupload.elements].filter(
          (el) => !el.checkValidity()
        )
      )
    }
  }
}

/* --- form handling, submit --- */

const isSubmitting = ref(false)

const approveAndSubmit = async () => {
  isSubmitting.value = true
  try {
    // "flatten/reduce" the {id:bool} object into an array (where false!)
    const excludeIds = Object.entries(attachments.autoApproveSelection)
      .filter((kv) => kv[1] === false).map((kv) => +kv[0])
    await approveAllUnredactedAttachments(excludeIds)
    await submitFetch()
    await publish()
    gotoStep()
  } catch (err) {
    // error from the partialUpdates/PATCHes looks like
    // { resolution: [ '"0" ist keine gültige Option'] }
    // { non_field_errors: [ 'Antwortnachrichten müssen...' ] }
    console.error('fetch submit error', err)
    error.value = err
  } finally {
    isSubmitting.value = false
  }
}

const isoNoonifyDate = (dateYmdStr) =>
  // "When the time zone offset is absent, date-only forms are interpreted as a UTC time
  // and date-time forms are interpreted as a local time."
  (new Date(dateYmdStr + 'T12:00:00')).toISOString()

const ymdifyDate = (date) =>
  `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`

const submitFetch = async () => {
  await requestPartialUpdate({
    path: { id: props.foirequest_id }, // TODO?
    body: {
      costs: values.costs,
      status: values.status,
      resolution: values.resolution,
    },
    throwOnError: true
  })
    .then(() => {
      console.info('requestPartialUpdate successful')
    })
  const messageBody = {
    is_response: values.is_response,
    sender_public_body: values.is_response ? values.public_body : null,
    recipient_public_body: values.is_response ? null : values.public_body,
  }
  if (values.date) messageBody.timestamp = isoNoonifyDate(values.date)
  if (values.registered_mail_date) messageBody.registered_mail_date = isoNoonifyDate(values.registered_mail_date)
  await messagePartialUpdate({
    path: { id: props.message.id },
    body: messageBody,
    throwOnError: true
  })
    .then(() => {
      console.info('messagePartialUpdate successful')
    })
  /*
  const action = document.forms.postupload.action
  const formdata = new FormData(document.forms.postupload)
  if (debug.value) {
    console.log('submit', { action, formdata })
  }
  return fetch(action, {
    method: 'post',
    headers: {
      'x-requested-with': 'fetch'
    },
    body: formdata
  })
    .then((response) => {
      if (!response.ok)
        throw new Error(
          `form submitFetch error ${response.status} ${response.statusText}`
        )
      return response.json()
    })
    .then((response) => {
      if ('errors' in response) {
        throw new Error(
          'form submitFetch error: ' + JSON.stringify(response.errors, false, 2)
        )
      }
      console.log('form submitFetch successful')
      gotoStep()
    })
    .catch((err) => {
      console.error('fetch submit errors', err)
      // TODO this will be replaced once we have an API instead of the form submit,
      // for now it is better than nothing.
      // Eventually this should trigger a modal and maybe
      // link to steps which are invalid?
      // Theoretical implementation now could be:
      // if 'date' in errors then link to STEP_ with linked <input type=date>
      alert(err.message)
    })
  */
}

const publish = () => {
  return messagePublishCreate({
    path: { id: props.message.id },
    throwOnError: true
  })
}

/* --- <online-help> interaction --- */

const onlineHelp = ref()

/* --- <attachment-manager> interaction --- */

onMounted(() => {
  // refreshAttachments()
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

const fileUploaderSucceeded = (uppyResult) => {
  addFromUppy(uppyResult, i18n.value.documentsUploadDefaultFilename)
    .then(() => {
      gotoStep()
    })
}

/* --- <file-uploader> interaction --- */

const fileUploader = ref()
const fileUploaderForceShow = ref(false)
onMounted(() => {
  document.body.addEventListener('dragover', () => fileUploaderForceShow.value = true)
  document.body.addEventListener('dragenter', () => fileUploaderForceShow.value = true)
})

/* --- <pdf-redaction> interaction --- */

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

/* --- state machine, functionality --- */

const firstStep = STEP_INTRO
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

onMounted(async () => {
  // TODO we only use props.message.attachments for this - use attachments store instead?
  await refreshAttachments()
  if (attachments.irrelevant.length > 0 && step.value === STEP_INTRO) {
    console.info('onMounted, skipped intro because irrelevant attachments present')
    gotoStep(STEP_DOCUMENTS_CONVERT)
  }
  else if (attachments.all.length > 0 && step.value === STEP_INTRO) {
    console.info('onMounted, skipped intro because attachments present')
    gotoStep(STEP_DOCUMENTS_OVERVIEW)
  }
})

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
        return STEP_DOCUMENTS_SORT
      }
      if (attachments.irrelevant.length > 0) {
        return STEP_DOCUMENTS_CONVERT
      }
      console.log('uploads were documents, not images, passing by image sorting')
      return STEP_MESSAGE_SENT_OR_RECEIVED
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.addLetter
    }
  },
  [STEP_DOCUMENTS_CONVERT]: {
    next: STEP_DOCUMENTS_OVERVIEW,
    onEnter: () => {
      guardBeforeunload(true)
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.letterUploadOrScan
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
      mobileHeaderTitle: i18n.value.letterUploadOrScan,
      documents: true,
      documentsUpload: false, // TODO check how many of these are still relevant => cleanup
      documentsHideSelection: true,
      documentsHidePdf: true,
      documentsImagesSimple: true
    }
  },
  [STEP_DOCUMENTS_CONVERT_PDF]: {
    next: STEP_DOCUMENTS_OVERVIEW,
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.letterUploadOrScan
    }
  },
  [STEP_DOCUMENTS_OVERVIEW]: {
    next: STEP_MESSAGE_SENT_OR_RECEIVED,
    onEnter: () => {
      pdfRedactionUploaded()
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.letterUploadOrScan,
      documents: true,
      documentsUpload: false,
      documentsHideSelection: true,
      // would make sense "if has geschwärzte docs", i.e. when we expect users to go back
      // documentsHighlightRedactions: true,
      documentsIconStyle: 'icon'
    }
  },
  [STEP_MESSAGE_SENT_OR_RECEIVED]: {
    next: STEP_MESSAGE_PUBLICBODY_CHECK,
    /* onBeforeNext: async () => {
      return await updateValue('sent')
      // todo handle validation
    }, */
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
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
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_MESSAGE_PUBLICBODY_UPDATE]: {
    next: STEP_MESSAGE_DATE,
    context: {
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
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
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
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      isGotoValid: () => validity.registered_mail_date
    }
  },
  [STEP_MESSAGE_STATUS]: {
    next: () => {
      if (!isDesktop.value && requestIsResolved.value)
        return STEP_MESSAGE_MESSAGE_RESOLUTION
      // TODO: replace all STEP_REDACTION_PICKER with `if uploadedDocuments.length === 1 ? ... : STEP_REDACTION_PICKER`
      if (!values.is_response) return STEP_REDACTION_PICKER
      return requestHadCosts.value
        ? STEP_MESSAGE_COST_CHECK_LAST
        : STEP_MESSAGE_COST_CHECK_ANY
    },
    onEnter: () => {
      updateValidity('status')
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      isGotoValid: () => validity.status
    }
  },
  [STEP_MESSAGE_MESSAGE_RESOLUTION]: {
    next: () => {
      if (values.is_reponse) return STEP_REDACTION_PICKER
      return requestHadCosts.value
        ? STEP_MESSAGE_COST_CHECK_LAST
        : STEP_MESSAGE_COST_CHECK_ANY
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_MESSAGE_COST_CHECK_ANY]: {
    next: () => {
      if (!isDesktop.value && requestUpdateCosts.value)
        return STEP_MESSAGE_COST_UPDATE
      return STEP_REDACTION_PICKER
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_MESSAGE_COST_CHECK_LAST]: {
    next: () => {
      if (!isDesktop.value && requestUpdateCosts.value)
        return STEP_MESSAGE_COST_UPDATE
      return STEP_REDACTION_PICKER
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      isGotoValid: () => {
        if (isDesktop.value && requestUpdateCosts.value) return validity.costs
        return true
      }
    }
  },
  [STEP_MESSAGE_COST_UPDATE]: {
    next: STEP_REDACTION_PICKER,
    onEnter: () => {
      updateValidity('costs')
    },
    context: {
      isGotoValid: () => validity.costs,
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_REDACTION_PICKER]: {
    next: () => {
      if (attachmentsSelectedPdfRedaction.value.length === 0)
        return STEP_DOCUMENTS_OVERVIEW_REDACTED
      return STEP_REDACTION_REDACT // TODO
    },
    onEnter: () => {
      pdfRedactionUploaded()
    },
    context: {
      progressStep: 2,
      mobileHeaderTitle: i18n.value.redact,
      documents: true,
      documentsUpload: false,
      documentsIconStyle: 'thumbnail',
      documentsShowAutoApprove: props.user_is_staff
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
      return STEP_DOCUMENTS_OVERVIEW_REDACTED
    },
    context: {
      progressStep: 2,
      mobileHeaderTitle: i18n.value.redact
    }
  },
  [STEP_DOCUMENTS_OVERVIEW_REDACTED]: {
    next: STEP_OUTRO,
    onEnter: () => {
      attachments.unselectSubset(attachments.relevant)
      attachmentsOverviewActions.value = false
      updateValidity('form')
      pdfRedactionUploaded()
    },
    context: {
      progressStep: 2,
      mobileHeaderTitle: i18n.value.preview,
      documents: true,
      documentsUpload: false,
      documentsHideSelection: true, // !(props.object_public && props.user_is_staff),
      documentsIconStyle: 'thumbnail',
      documentsHighlightRedactions: true,
      documentsShowAutoApprove: props.user_is_staff
    }
  },
  [STEP_OUTRO]: {
    next: STEP_OUTRO,
    onEnter: () => {
      guardBeforeunload(false)
    },
    context: {
      progressStep: 2,
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
  'digraph "postupload" {\n' +
  Object.keys(c)
    .map((state) => `  "${state}";\n`)
    .join('') +
  Object.keys(c)
    .map((from) =>
      c[from].next
        .toString()
        .match(/\bSTEP_\w+/g)
        .map((to) => `  "${from}" -> "${to}";\n`)
        .join('')
    )
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
  <online-help ref="onlineHelp" />

  <simple-stepper class="sticky-top position-md-static" :step="stepContext.progressStep"
    :steps="['Hochladen', 'Infos eingeben', 'Schwärzen']">
    <template v-if="step === STEP_OUTRO">
      <small>{{ i18n.done }}</small>
    </template>
    <template v-else>
      {{ i18n.step }} <strong>{{ stepContext.progressStep + 1 }}/3</strong>:
      {{ stepContext.mobileHeaderTitle }}
    </template>
  </simple-stepper>

  <div class="container">
    <!-- TODO button does not support going back throug pdfRedactionCurrentIndex-->
    <div v-if="step === STEP_INTRO" class="my-3">
      <a class="btn btn-link text-decoration-none ps-0" href="../..">← <u>{{ i18n.cancel }}</u></a>
    </div>
    <div v-else-if="step !== STEP_OUTRO" class="my-3">
      <a @click="backStep" class="btn btn-link text-decoration-none ps-0">← <u>{{ i18n.back }}</u></a>
    </div>
  </div>

  <div v-if="error" class="container">
    <div class="alert alert-danger alert-dismissible show" role="alert">
      <h4 class="alert-heading">
        {{ i18n.error || 'Error' }}<!-- TODO i18n -->
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
                go to <!--{{ fieldErrorStep[key] }}--> <!-- TODO i18n -->
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                @click="gotoStep(STEP_DOCUMENTS_OVERVIEW_REDACTED)"
                >
                return to submit<!-- TODO i18n -->
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
    <div>draft = {{ draft }}</div>
    <div>step={{ step }}</div>
    <div>history={{ stepHistory.join(' ') }}</div>
    <div>stepContext={{ stepContext }}</div>
    <div>isGotoValid={{ isGotoValid }}</div>
    <div>attachments.autoApproveSelection={{ attachments.autoApproveSelection }}</div>
    <span>
      <!-- eslint-disable-next-line vue/no-mutating-props -->
      <button type="button" @click="user_is_staff = !user_is_staff">
        {{ user_is_staff ? '☑' : '☐' }} staff
      </button>
    </span>
    <span>isDesktop={{ isDesktop }}</span>
    <button class="btn btn-secondary btn-sm" type="button" @click="approveAndSubmit"
      style="font-size: 50%; margin-left: 1em">
      approveAndSubmit()
    </button>
    <button class="btn btn-secondary btn-sm" type="button" @click="submitFetch"
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
    <!--<span class="debug">
          {{ { pbv: props.form.fields.publicbody.value, pbii:  props.form.fields.publicbody?.initial?.id, opbi: object_public_body_id } }}
        </span>-->
    <!-- <span class="debug">formStatus={{formStatus}},</span> -->
    <!-- <span class="debug">formDoUpdateCost={{formDoUpdateCost}},</span> -->
    <!--<span class="debug">{{documentsSelectedPdfRedaction}}</span>-->
    <!--<span class="debug">documentsSelectedPdfRedaction={{ documentsSelectedPdfRedaction.map(d => d.id).join(',') }}</span>-->
    <!--
    <details v-if="form.nonFieldErrors.length">
      <summary class="debug">DEBUG form.nonFieldErrors</summary>
      <pre>{{ form.nonFieldErrors }}</pre>
    </details>
    <details v-if="Object.keys(form.errors).length">
      <summary class="debug">DEBUG form.errors</summary>
      <pre>{{ form.errors }}</pre>
    </details>
    -->
  </details>
  <pre style="color: darkred">
values={{ values }}
formStatusChoices={ formStatusChoices }
  </pre>

  <div class="step-container">
    <div v-show="step === STEP_INTRO" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="row my-5 justify-content-center">
            <!--
                <div class="col-md-6">
                  <button disabled class="btn btn-outline-primary d-block w-100">
                    <i class="fa fa-camera"></i>
                    {{ i18n.scanDocuments }}
                  </button>
                  <p class="mt-1">
                    {{ i18n.scanDocumentsAddendum }}
                  </p>
                </div>
                <div class="col-md-6">
                  <button
                    type="button"
                    @click="stepAndUppyClick"
                    class="btn btn-outline-primary d-block w-100">
                    <i class="fa fa-upload"></i>
                    {{ i18n.uploadFiles }}
                  </button>
                  <p class="mt-1">
                    {{ i18n.uploadFilesAddendum }}
                  </p>
                </div>
                -->
            <div v-if="config.url.mobileAppContent" class="col-md-6">
              <div v-if="mobileAppContent !== null" v-html="mobileAppContent"></div>
              <div v-else>
                <div class="spinner-border" role="status">
                  <span class="visually-hidden">{{ i18n.loading }}</span>
                </div>
              </div>
            </div>
            <div class="col-md-6">
              <button
                type="button"
                @click="fileUploader.clickFilepick()"
                v-if="!fileUploaderForceShow"
                class="btn btn-outline-primary btn-lg d-block w-100"
              >
                <i class="fa fa-upload fa-2x"></i><br />
                {{ i18n.uploadFiles }}
              </button>
              <file-uploader
                :config="config"
                :allowed-file-types="config.settings.allowed_filetypes"
                :auto-proceed="true"
                :show-uppy="fileUploaderForceShow"
                ref="fileUploader"
                @upload-success="fileUploaderSucceeded"
                />
            </div>
            <!-- TODO
            <div class="col-md-6">
              QR code goes here
            </div>
            -->
          </div>
          <div class="alert alert-warning">
            <h4><i class="fa fa-lightbulb-o fa-lg"></i> Tipp</h4>
            <p v-html="i18n.redactLaterHint1"></p>
            <p v-html="i18n.redactLaterHint2"></p>
          </div>
          <div class="alert alert-warning">
            <h4>
              <i class="fa fa-exclamation-circle fa-lg"></i>
              {{ i18n.new }}
            </h4>
            <p>
              {{ i18n.newWarning }}
            </p>
            <p v-html="i18n._('newLinkOldFlow', { url: config.url.legacyPostupload })
              "></p>
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
          <attachments-table
            :subset="attachments.irrelevant"
            actions table-selection action-delete selection-action-delete badges-type
            />
        </div>
        <!-- irrelevant attachments re-appear after a refresh;
           should they be (were they?) permantly marked "processed" or deleted?
           "fresh" images have can_delete=true (among other unrelated props)
           "converted" images don't...
           not sure if there is a good distinction/semantics here.
           -->
        <images-converter
          @converted="() => { if (attachments.irrelevant.length === 0) gotoStep() }"
          />
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_SORT" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9 fw-bold">
          {{ i18n.documentsDragOrder }}
        </div>
        <image-document-pages-sortable
          :idx="0"
          show-rotate
          />
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
        <div v-if="attachments.images[0]" class="documents-filename p-2 my-3 mx-auto">
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
          <attachments-table :subset="attachments.relevant" action-delete cards-bg-transparent :as-card-threshold="0" />
          <!-- TODO after a reload we land here. it might be good to also display "images" -->
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_SENT_OR_RECEIVED" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 1 von 5</div>
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
          <div class="step-questioncounter">Frage 2 von 5</div><!-- FIXME i18n !! -->
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="!values.is_response">
              {{ i18n.messagePublicbodyCheckTo }}
            </template>
            <template v-else>
              {{ i18n.messagePublicbodyCheckFrom }}
            </template>
          </label>
          <div style="margin: 1em 0; font-style: italic">
            {{ props.foirequest_public_body.name }}
          </div>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { value: true, label: 'Ja.' },
            { value: false, label: 'Nein, andere Behörde wählen' }
          ]" :key="choiceIndex">
            <input type="radio" required="" class="form-check-input" v-model="messagePublicBodyIsDefault"
              :id="'id_pbisdefault_' + choiceIndex" :value="choice.value" />
            <label class="form-check-label" :for="'id_pbisdefault_' + choiceIndex">{{ choice.label }}</label>
          </div>
          <input type="hidden" name="publicbody" v-if="messagePublicBodyIsDefault" :value="formPublicbodyId" />
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
          <publicbody-chooser v-if="!messagePublicBodyIsDefault" :search-collapsed="false" scope="postupload_publicbody"
            name="publicbody" :config="config" :value="props.foirequest_public_body.id" list-view="resultList"
            :show-filters="false" :show-badges="false" :show-found-count-if-idle="false"
            @update="updatePublicBody"
            />
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_DATE" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 3 von 5</div>
          <label class="fw-bold form-label field-required" for="id_date">
            {{ i18n.messageDate }}
            <!--{{ form.fields.date.label }}-->
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
            <input class="form-check-input" type="checkbox" v-model="values.is_registered_mail"
              id="id_is_registered_mail" />
            <label class="form-check-label" for="id_is_registered_mail">
              {{ i18n.messageIsRegisteredMail }}
              <span type="button" v-bs-tooltip tabindex="0" data-bs-toggle="tooltip" data-bs-placement="bottom"
                :title="i18n.messageRegisteredMailInfo">
                <i class="fa fa-info-circle"></i>
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_DATE_REGISTERED_MAIL ||
      (isDesktop && step === STEP_MESSAGE_DATE && values.is_registered_mail)
      " class="container">
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold form-label field-required" for="id_registered_mail">
            {{ i18n.messageDateRegisteredMail }}
          </label>
          <!-- TODO set min/max? -->
          <input type="date" class="form-control" id="id_registered_mail_date" name="registered_mail_date"
            :required="values.is_registered_mail" @input="updateValidity('registered_mail_date')"
            v-model="values.registered_mail_date" />
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_STATUS" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 4 von 5</div>
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
            <!-- {{ status_form.fields.resolution.label }} -->
            {{ i18n.messageResolution }}
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in requestResolutionChoices" :key="choice.value">
            <input type="radio" name="resolution" :required="requestIsResolved" class="form-check-input"
              v-model="values.resolution"
              :id="'id_resolution_' + choiceIndex" :value="choice.value" />
            <label class="form-check-label" :for="'id_resolution_' + choiceIndex">{{ choice.label }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_COST_CHECK_ANY" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 5 von 5</div>
          <label class="fw-bold col-form-label">
            {{ i18n.messageCostCheck }}
          </label>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { label: 'Nein.', value: false },
            { label: 'Ja.', value: true }
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
          <div class="step-questioncounter">Frage 5 von 5</div>
          <!-- TODO: i18n: in DE, the amount format is not l10n: 1.00 instead of 1,00
            also, API returns floats, so this actually should be decimalized i18n-awarely...
            (or provided as a formatted string by the API)
           -->
          <label
            class="fw-bold col-form-label"
            for="id_nowcost"
            v-html="i18n._('messageCostCheckLast', { amount: requestOldCosts })"
            ></label>
          <div class="form-check" v-for="(choice, choiceIndex) in [
            { label: 'Ja.', value: false },
            { label: 'Nein.', value: true }
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
              <input type="number" name="costs" id="id_costs" class="form-control col-3" inputmode="decimal"
                style="appearance: textfield; text-align: right" min="0" max="1000000000" step="0.01"
                v-model="values.costs" @input="updateValidity('costs')" :class="{
                  'is-invalid': validity.costs === false,
                  'is-valid': validity.costs === true
                }" />
              <span class="input-group-text">Euro<!-- TODO i18n--></span>
            </div>
            <!--<div class="form-text">{{ status_form.fields.costs.help_text }}</div>-->
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
          <attachments-table :subset="attachments.relevant" table-selection selection-buttons :as-card-threshold="0">
            <template #after-row="slotProps">
              <label class="d-flex flex-column position-absolute position-md-static top-0 end-0 py-3 px-1">
                <!-- like v-model, but default true -->
                <input
                  v-if="!slotProps.attachment.approved"
                  type="checkbox"
                  :checked="attachments.autoApproveSelection[slotProps.attachment.id] !== false"
                  @input="(evt) => { attachments.autoApproveSelection[slotProps.attachment.id] = evt.target.checked }"
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
            <template #after-card="slotProps">
              <label
                v-if="!slotProps.attachment.approved"
                class="text-center"
                >
                <input
                  type="checkbox"
                  :checked="attachments.autoApproveSelection[slotProps.attachment.id] !== false"
                  @input="(evt) => { attachments.autoApproveSelection[slotProps.attachment.id] = evt.target.checked }"
                  />
                {{ i18n.publish }}*
              </label>
              <div v-else>
                {{ i18n.alreadyPublished }}
              </div>
            </template>
            <template #after-table>
              <div class="text-end px-2">
                {{ i18n.documentsApproveLater }}
                ⮥
              </div>
            </template>
            <template #after-cards>
              <div class="text-end px-2">
                * {{ i18n.documentsApproveLater }}
              </div>
            </template>
          </attachments-table>
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
              <django-slot name="redaction_explanation"></django-slot>
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
        <pdf-redaction
          :class="pdf-redaction-tool"
          v-if="pdfRedactionCurrentDoc"
          :key="pdfRedactionCurrentDoc.id"
          :pdf-path="pdfRedactionCurrentDoc.file_url"
          :attachment-url="pdfRedactionCurrentDoc.anchor_url"
          :auto-approve="attachments.autoApproveSelection[pdfRedactionCurrentDoc.id] !== false"
          :post-url="
            config.url.redactAttachment.replace(
              '/0/',
              '/' + pdfRedactionCurrentDoc.id + '/'
            )
          "
          :approve-url="
            config.url.approveAttachment.replace(
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
        </pdf-redaction>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW_REDACTED" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="fw-bold col-form-label">
            {{ i18n.documentsOverview }}
          </div>
          <attachments-table
            :subset="attachments.relevant.filter(att => !att.redacted)"
            badges-redaction badges-resolution
            :actions="attachmentsOverviewActions"
            >
            <template #before-cards>
              <div class="text-end mb-2">
                <button
                  type="button"
                  class="btn btn-link"
                  @click="() => attachmentsOverviewActions = !attachmentsOverviewActions"
                  >
                  {{ attachmentsOverviewActions ? i18n.done : i18n.edit }}
                </button>
              </div>
            </template>
            <template #before-table>
            </template>
          </attachments-table>
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
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW" class="container">
      <div class="row justify-content-center">
        <div class="col-sm-9 col-md-6 mt-3">
          <button type="button" class="btn btn-outline-primary d-block w-100 mb-3" :disabled="true">
            <i class="fa fa-plus"></i>
            {{ i18n.scanDocumentsAnother }}
          </button>
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100"
            @click="gotoStep(STEP_DOCUMENTS_INTRO)"
          >
            <i class="fa fa-plus"></i>
            {{ i18n.uploadFilesAnother }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="sticky-bottom mt-auto mt-md-0 bg-body py-2">
    <div class="container">
      <div class="row justify-content-center">
        <div class="col-md-9 col-lg-6 text-center">
          <template v-if="step === STEP_REDACTION_REDACT">
            <button type="button" @click="pdfRedactionRedact()" class="btn btn-primary d-block w-100"
              :disabled="pdfRedactionProcessing">
              <span class="spinner-border spinner-border-sm" v-show="pdfRedactionProcessing" role="status"
                aria-hidden="true" />
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
              @click="approveAndSubmit"
              class="btn btn-primary d-block w-100"
              :disabled="isSubmitting || !validity.form"
            >
              <span
                class="spinner-border spinner-border-sm"
                v-show="isSubmitting"
                role="status"
                aria-hidden="true"
              />
              {{ i18n.confirm }}
            </button>
            <div class="mt-2" v-if="!validity.form">
              <small>
                {{ i18n.formHasErrors }}
                <!-- TODO: we could go through all elements, validate, and report here -->
              </small>
            </div>
            <div class="mt-2" v-if="!object_public">
              <small>
                {{ i18n.requestNonPublicHint }}
              </small>
            </div>
          </template>
          <template v-else-if="step === STEP_OUTRO">
            <button type="button" @click="submitForm" class="btn btn-primary d-block w-100">
              {{ i18n.requestShow }}
            </button>
          </template>
          <template v-else-if="step === STEP_INTRO">
            <!-- should be blank -->
            <button v-if="debug" type="button" @click="gotoStep()" class="action btn btn-outline-primary btn-sm mt-1">
              DEBUG skip
            </button>
          </template>
          <template v-else-if="step === STEP_DOCUMENTS_SORT">
            <button type="button" @click="gotoStep()" class="btn btn-primary d-block w-100">
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
            <button v-else type="button" @click="gotoStep()" class="btn btn-primary d-block w-100">
              {{ i18n.next }}
            </button>
          </template>
          <template v-else-if="step === STEP_MESSAGE_DATE">
            <button type="button" :disabled="!isGotoValid" @click="gotoStep()" class="btn btn-primary d-block w-100">
              {{ i18n.next }}
            </button>
            <button v-if="debug" type="button" @click="debugSkipDate"
              class="btn btn-outline-primary btn-sm mt-1 d-block w-100">
              DEBUG set today
            </button>
          </template>
          <template v-else>
            <button type="button" @click="gotoStep()" :disabled="!isGotoValid" class="btn btn-primary d-block w-100">
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
</style>
