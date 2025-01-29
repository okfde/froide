<script setup>
import { ref, reactive, computed, defineProps, nextTick, onMounted } from 'vue'
import SimpleStepper from './simple-stepper.vue'
// import PublicbodyChooser from '../publicbody/publicbody-chooser'
import PublicbodyChooser from '../publicbody/publicbody-beta-chooser'
// TODO linter wrong? the two above are just fine...
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import DocumentUploader from '../docupload/document-uploader.vue'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import PdfRedaction from '../redaction/pdf-redaction.vue'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import OnlineHelp from './online-help.vue'
import { listFoiMessageDrafts, createFoiMessageDraft, partialUpdateFoiMessageDraft } from '../../api/index.ts'
import { useI18n } from '../../lib/i18n'
import { vBsTooltip } from '../../lib/vue-bootstrap'
import { useIsDesktop } from '../../lib/vue-helpers-layout'
import { scrollNavIntoViewIfNecessary, guardBeforeunload } from '../../lib/misc'

import { resolution } from '../../api/index.ts'

const props = defineProps({
  config: Object,
  // form: Object,
  // message: Object,
  // status_form: Object,
  foirequest: Object,
  foirequest_id: String,
  foirequest_apiurl: String,
  foirequest_costs: Object,
  object_public_body_id: String,
  object_public_body: Object,
  object_public: Boolean,
  date_min: String,
  date_max: String,
  user_is_staff: Boolean
})

const { i18n } = useI18n(props.config)

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

const createOrRetrieveLastDraft = async () => {
  const requestParam = { query: { request: props.foirequest_id } }
  try {
    const drafts = await listFoiMessageDrafts({ ...requestParam, throwOnError: true })
    if (drafts.data.objects.length) {
      // TODO: this is not the "newest"
      //   would have to get last page (or increase limit)
      //   either "while drafts.meta.next"
      //   or { limit: 1, offset: results.meta.total_count - 1 }
      draft.value = drafts.data.objects[drafts.data.objects.length - 1]
      // unnecessary, we already get all data from listFoi…
      //   await retrieveFoiMessageDraft({ path: { id: newestDraft.resource_uri }})
    } else {
      draft.value = await createFoiMessageDraft({
        body: requestParam,
        throwOnError: true
        // body.timestamp: ...
      })
    }
    formSent.value = draft.value.sent
    values.sent = draft.value.sent
    /*
      draft.value = r
      formSent.value = r.is_response
      formStatus.value = r.status
      formStatusWasResolved.value = r.status === 'resolved'
      */
  } catch (e) {
    error.value = e.message
  }
}

const updateValue = async (key) => {
  return partialUpdateFoiMessageDraft({
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

/* --- form handling --- */

/* untangle ambiguous semantics:
 * there is message.sent, but this is not the same.
 * sent in the Form's context means "negated is_response"
 * TODO: this should be cleaned up at the model level.
 */
// const formSent = ref(props.message?.is_response ? '0' : '1')
const formSent = ref(false) // computed(() => draft.value.is_response ? '0' : '1')
// const formIsSent = computed(() => formSent.value === '1')
// const formIsSent = computed(() => draft.value.is_response)

const formSentChoices = [
  { value: true, label: 'true TODO i18n' },
  { value: false, label: 'false TODO i18n' },
]

const formPublicbodyIsDefault = ref(true)

const formPublicBodyIsDefaultChoices = [
  { value: true, label: 'Ja.' },
  { value: false, label: 'Nein, andere Behörde wählen' }
]

// const formStatus = ref(
//   props.status_form.fields.status.value ||
//     props.status_form.fields.status.initial
// )
const formStatus = ref('')
// const formStatusWasResolved = formStatus.value === 'resolved'
const formStatusWasResolved = ref(false)
const formStatusIsResolved = computed(() => formStatus.value === 'resolved')

// TODO i18n
const formStatusLabels = {
  SUCCESSFUL: "Request Successful",
  PARTIALLY_SUCCESSFUL: "Request partially successful",
  NOT_HELD: "Information not held",
  REFUSED: "Request refused",
  USER_WITHDREW_COSTS: "Request was withdrawn due to costs",
  USER_WITHDREW: "Request was withdrawn",
}

// remove nonsensical combos
const formStatusChoices = computed(() => {
  const badCombinations = formSent.value
    ? ['', 'successful', 'partially_successful', 'not_held', 'refused']
    : ['user_withdrew_costs']
  // return props.status_form.fields.resolution.choices.filter(
  return Object.keys(resolution)
    .filter((key) => !badCombinations.includes(resolution[key]))
    .map((key) => ({ value: resolution[key], label: formStatusLabels[key] }))
})


// const formCost = props.status_form.fields.costs.initial?.intValue || 0
// const formHasHadCost = formCost > 0
const formHasHadCost = props.foirequest_costs.intValue > 0
const formDoUpdateCost = ref(false)
const formDoUpdateCostChoices = [
  { label: 'Ja.', value: true },
  { label: 'Nein.', value: false },
]

const formPublicbodyId = ref(props.object_public_body_id)
  // TODO
  // props.form.fields.publicbody.value ||
  // props.form.fields.publicbody?.initial?.id?.toString() ||

const formPublicbodyLabel = props.object_public_body?.name || 'Error'

const values = reactive({
  sent: undefined,
  // FIXME date doesn't populate from a saved form?
  // date: props.form.fields.date.value,
  date: '', // draft.value.timestamp,
  registered_mail_date: '', //: props.form.fields.registered_mail_date.value,
  costs: props.foirequest_costs.strValue,
    // props.status_form.fields.costs.value?.strValue ||
    //props.status_form.fields.costs.initial.strValue,
  is_registered_mail: false
})

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

const submitForm = async () => {
  document.forms.postupload.submit()
}

const approveAndSubmit = async () => {
  isSubmitting.value = true
  try {
    await documentUploader.value.approveUnredacted()
    await submitFetch()
    gotoStep()
  } catch (err) {
    console.error('fetch submit error', err)
    alert('error' + JSON.stringify(err))
  } finally {
    isSubmitting.value = false
  }
}

const submitFetch = async () => {
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
}

/* --- <online-help> interaction --- */

const onlineHelp = ref()

/* --- <document-uploader> interaction --- */

const documentUploader = ref()

const documentsSelectedPdfRedaction = ref([])

const documentsImagesConverting = ref(false)
const documentsConvertImages = () => {
  if (documentUploader.value.$refs.imageDocument.length === 0) {
    console.log('no images to convert')
    gotoStep()
    return
  }
  documentsImagesConverting.value = true
  // XXX wild mix of Vue2&3 refs, not the cleanest, but a bus was basically impossible
  // we are calling a grand-child component's method
  documentUploader.value.$refs.imageDocument?.[0]?.convertImages?.()
  // ^child              ^vue2 ^grandchild...REN!  ^method
  // alternative: pass a prop, watch it, react?
}
const documentsImagesDocumentFilenameDefault =
  i18n.value.documentsUploadDefaultFilename
const documentsImagesDocumentFilename = ref(
  documentsImagesDocumentFilenameDefault
)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const documentsImagesDocumentFilenameNormalized = computed(() =>
  documentsImagesDocumentFilename.value.replace(/\.pdf$/, '')
)

const documentsBasicOperations = ref(false)

const documentUploaderSelectAll = (val) => {
  documentUploader.value.setAllSelect(val)
}

const stepAndUppyClick = () => {
  gotoStep()
  // wait until gotoStep unveils uppy in DOM (v-if)
  nextTick(() => {
    const button = documentUploader.value.$el.querySelector(
      '.uppy-Dashboard-browse'
    )
    console.log('# uppyClick', button)
    button.click()
  })
}

const documentsImageMode = ref(false)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const documentsImagesAdded = () => {
  if (step.value !== STEP_DOCUMENTS_UPLOAD) {
    return
  }
  documentsImageMode.value = true
  gotoStep()
}
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const documentsDocumentsAdded = () => {
  if (step.value !== STEP_DOCUMENTS_UPLOAD) {
    return
  }
  gotoStep()
}
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const documentsImagesConverted = () => {
  documentsImagesConverting.value = false
  if (step.value !== STEP_DOCUMENTS_CONVERT_PDF) {
    console.warn("conversion shouldn't have happened here")
    return
  }
  gotoStep()
}

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
  return documentsSelectedPdfRedaction.value[pdfRedactionCurrentIndex.value]
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
  // TODO handle errors?
  // XXX again, we're calling child's method, could handle attachments here, store-like,
  //   and pass as a "override prop" to the components
  documentUploader.value.refreshAttachments()
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
const STEP_DOCUMENTS_UPLOAD = 'STEP_DOCUMENTS_UPLOAD' // 1110
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
    next: STEP_DOCUMENTS_UPLOAD,
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.addLetter
    }
  },
  [STEP_DOCUMENTS_UPLOAD]: {
    next: () => {
      if (documentsImageMode.value) {
        console.log(
          'uploads were documents, not images, passing by image sorting'
        )
        return STEP_DOCUMENTS_SORT
      }
      return STEP_MESSAGE_SENT_OR_RECEIVED
    },
    onEnter: () => {
      guardBeforeunload(true)
      documentsImagesDocumentFilename.value =
        documentsImagesDocumentFilenameDefault
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.letterUploadOrScan,
      documents: true,
      documentsUpload: true,
      documentsHideSelection: true,
      documentsHidePdf: true,
      documentsImagesSimple: true
    }
  },
  [STEP_DOCUMENTS_SORT]: {
    next: STEP_DOCUMENTS_CONVERT_PDF,
    onBack: () => {
      // go back two steps, to INTRO
      stepHistory.pop()
    },
    context: {
      progressStep: 0,
      mobileHeaderTitle: i18n.value.letterUploadOrScan,
      documents: true,
      documentsUpload: false,
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
    onBeforeNext: async () => {
      return await updateValue('sent')
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation
    }
  },
  [STEP_MESSAGE_PUBLICBODY_CHECK]: {
    next: () => {
      if (isDesktop.value) return STEP_MESSAGE_DATE
      return formPublicbodyIsDefault.value
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
      if (!isDesktop.value && formStatusIsResolved.value)
        return STEP_MESSAGE_MESSAGE_RESOLUTION
      // TODO: replace all STEP_REDACTION_PICKER with `if uploadedDocuments.length === 1 ? ... : STEP_REDACTION_PICKER`
      // TODO test formSent
      if (formSent.value) return STEP_REDACTION_PICKER
      return formHasHadCost
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
      // TODO test formSent
      if (formSent.value) return STEP_REDACTION_PICKER
      return formHasHadCost
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
      if (!isDesktop.value && formDoUpdateCost.value)
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
      if (!isDesktop.value && formDoUpdateCost.value)
        return STEP_MESSAGE_COST_UPDATE
      return STEP_REDACTION_PICKER
    },
    context: {
      progressStep: 1,
      mobileHeaderTitle: i18n.value.enterInformation,
      isGotoValid: () => {
        if (isDesktop.value && formDoUpdateCost.value) return validity.costs
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
      if (documentsSelectedPdfRedaction.value.length === 0)
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
        documentsSelectedPdfRedaction.value.length - 1
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
      documentsBasicOperations.value = false
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

onMounted(() => {
  createOrRetrieveLastDraft()
})

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

  <simple-stepper
    class="sticky-top position-md-static"
    :step="stepContext.progressStep"
    :steps="['Hochladen', 'Infos eingeben', 'Schwärzen']"
  >
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
      <a class="btn btn-link text-decoration-none ps-0" href="../.."
        >← <u>{{ i18n.cancel }}</u></a
      >
    </div>
    <div v-else-if="step !== STEP_OUTRO" class="my-3">
      <a @click="backStep" class="btn btn-link text-decoration-none ps-0"
        >← <u>{{ i18n.back }}</u></a
      >
    </div>
  </div>

  <div v-if="error" class="container">
    <div class="alert alert-danger" role="alert">
      <div>Fehler</div>
      <dl v-if="typeof error === 'object'">
        <template v-for="(value, key) in error" :key="key">
          <dt>{{ key }}</dt>
          <dd>{{ value.join?.(', ') || value }}</dd>
        </template>
      </dl>
    </div>
  </div>

  <details v-if="debug" class="container">
    <summary class="DEBUG">DEBUG</summary>
    <div>draft = {{ draft }}</div>
    <div>step={{ step }}</div>
    <div>history={{ stepHistory.join(' ') }}</div>
    <div>stepContext={{ stepContext }}</div>
    <div>isGotoValid={{ isGotoValid }}</div>
    <span>
      <!-- eslint-disable-next-line vue/no-mutating-props -->
      <button type="button" @click="user_is_staff = !user_is_staff">
        {{ user_is_staff ? '☑' : '☐' }} staff
      </button>
    </span>
    <span>isDesktop={{ isDesktop }}</span>
    <button
      class="btn btn-secondary btn-sm"
      type="submitForm"
      style="font-size: 50%; margin-left: 1em"
    >
      submit/save
    </button>
    <button
      class="btn btn-secondary btn-sm"
      type="button"
      @click="submitFetch"
      style="font-size: 50%; margin-left: 1em"
    >
      submit/fetch
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
            <div class="col-md-6">
              <button
                type="button"
                @click="stepAndUppyClick"
                class="btn btn-outline-primary btn-lg d-block w-100"
              >
                <i class="fa fa-upload fa-2x"></i><br />
                {{ i18n.uploadFiles }}
              </button>
            </div>
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
            <p
              v-html="
                i18n._('newLinkOldFlow', { url: config.url.legacyPostupload })
              "
            ></p>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_UPLOAD">
      <!-- document-uploader see below -->
    </div>
    <div v-show="step === STEP_DOCUMENTS_SORT" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9 fw-bold">
          {{ i18n.documentsDragOrder }}
        </div>
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
        <div class="documents-filename p-2 my-3 mx-auto">
          <div class="form-group">
            <input
              id="documents_filename"
              v-model="documentsImagesDocumentFilename"
              class="form-control"
            />
            <label for="documents_filename">
              {{ i18n.changeFilename }}
            </label>
          </div>
        </div>
      </div>
    </div>
    <!-- there is another for this step, further down below document-uploader -->
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="fw-bold">
            {{ i18n.documentsAvailable }}
          </div>
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
          <div class="form-check"
            v-for="(choice, c) in formSentChoices"
            :key="c"
            >
            <input
              type="radio"
              name="sent"
              v-model="values.sent"
              required=""
              class="form-check-input"
              :id="'id_sent_' + c"
              :value="choice.value"
            />
            <label class="form-check-label" :for="'id_sent_' + c">{{
              choice.label
            }}</label>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_PUBLICBODY_CHECK" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 2 von 5</div>
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="formSent">
              {{ i18n.messagePublicbodyCheckTo }}
            </template>
            <template v-else>
              {{ i18n.messagePublicbodyCheckFrom }}
            </template>
          </label>
          <div style="margin: 1em 0; font-style: italic">
            {{ formPublicbodyLabel }}
          </div>
          <div
            class="form-check"
            v-for="(choice, c) in formPublicBodyIsDefaultChoices"
            :key="c"
          >
            <input
              type="radio"
              required=""
              class="form-check-input"
              v-model="formPublicbodyIsDefault"
              :id="'id_pbisdefault_' + c"
              :value="choice.value"
            />
            <label
              class="form-check-label"
              :for="'id_pbisdefault_' + c"
              >{{ choice.label }}</label
            >
          </div>
          <!--input
            type="hidden"
            name="publicbody"
            v-if="formPublicbodyIsDefault"
            :value="formPublicbodyId"
          /-->
        </div>
      </div>
    </div>
    <div
      v-show="
        step === STEP_MESSAGE_PUBLICBODY_UPDATE ||
        (isDesktop &&
          step === STEP_MESSAGE_PUBLICBODY_CHECK &&
          !formPublicbodyIsDefault)
      "
      class="container"
    >
      <!-- appears "indented" on md=isDesktop viewport -->
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="formSent === '1'">
              {{ i18n.messagePublicbodyUpdateTo }}
            </template>
            <template v-else>
              {{ i18n.messagePublicbodyUpdateFrom }}
            </template>
          </label>
          <!-- TODO list-view=resultList has no pagination, but betaList doesnt work yet? -->
          <publicbody-chooser
            v-if="!formPublicbodyIsDefault"
            :search-collapsed="false"
            scope="foo_publicbody"
            name="publicbody"
            :config="config"
            :form="form"
            :value="formPublicbodyId"
            list-view="resultList"
            :show-filters="false"
            :show-badges="false"
            :show-found-count-if-idle="false"
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
          <input
            id="id_date"
            class="form-control"
            type="date"
            name="date"
            v-model="values.date"
            :class="{
              'is-invalid': validity.date === false,
              'is-valid': validity.date === true
            }"
            required
            :min="props.date_min"
            :max="props.date_max"
            @input="updateValidity('date')"
          />
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
          <div class="step-questioncounter">Frage 4 von 5</div>
          <label class="fw-bold form-label" for="id_subject">
            <template v-if="!formSent && formStatusWasResolved">
              {{ i18n.messageStatusIsResolvedAfterReceivedStill }}
            </template>
            <template v-if="!formSent && !formStatusWasResolved">
              {{ i18n.messageStatusIsResolvedAfterReceived }}
            </template>
            <template v-if="formSent && formStatusWasResolved">
              {{ i18n.messageStatusIsResolvedAfterSentStill }}
            </template>
            <template v-if="formSent && !formStatusWasResolved">
              {{ i18n.messageStatusIsResolvedAfterSent }}
            </template>
          </label>
          <div
            class="form-check"
            v-for="choice in formStatusChoices"
            :key="choice.value"
          >
            <input
              type="radio"
              name="status"
              required=""
              class="form-check-input"
              :id="'id_status_' + choice.value"
              v-model="formStatus"
              :value="choice.value"
              @input="updateValidity('status')"
            />
            <label class="form-check-label" :for="'id_status_' + choice.value">
              <template v-if="formStatusWasResolved">
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
    <div
      v-show="
        step === STEP_MESSAGE_MESSAGE_RESOLUTION ||
        (isDesktop && step === STEP_MESSAGE_STATUS && formStatusIsResolved)
      "
      class="container"
    >
      <div class="row justify-content-center">
        <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
          <label class="fw-bold col-form-label" for="id_resolution">
            {{ i18n.messageResolution }}
          </label>
          <div
            class="form-check"
            v-for="choice  in formStatusChoices"
            :key="choice.value"
          >
            <input
              type="radio"
              name="resolution"
              :required="formStatusIsResolved"
              class="form-check-input"
              :id="'id_resolution_' + choice.value"
              :value="choice"
              :x-checked="
                draft.status === choice
              "
            />
            <label
              class="form-check-label"
              :for="'id_resolution_' + choice.value"
              >{{ choice.label }}</label
            >
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
          <div
            class="form-check"
            v-for="(choice, c) in formDoUpdateCostChoices"
            :key="c"
          >
            <input
              type="radio"
              required=""
              class="form-check-input"
              v-model="formDoUpdateCost"
              :id="'id_nowcost_' + c"
              :value="choice.value"
            />
            <label
              class="form-check-label"
              :for="'id_nowcost_' + c"
              >{{ choice.label }}</label
            >
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_MESSAGE_COST_CHECK_LAST" class="container">
      <div class="row justify-content-center">
        <div class="col-lg-9">
          <div class="step-questioncounter">Frage 5 von 5</div>
          <!-- TODO: i18n: in DE, the amount format is not l10n: 1.00 instead of 1,00 -->
          <label
            class="fw-bold col-form-label"
            for="id_nowcost"
            v-html="
              i18n._('messageCostCheckLast', {
                amount:
                  props.foirequest_costs.strValue ||
                  'error'
              })
            "
          ></label>
          <div
            class="form-check"
            v-for="(choice, c) in formDoUpdateCostChoices"
            :key="c"
          >
            <input
              type="radio"
              required=""
              class="form-check-input"
              v-model="formDoUpdateCost"
              :id="'id_nowcost_' + c"
              :value="choice.value"
            />
            <label
              class="form-check-label"
              :for="'id_nowcost_' + c"
              >{{ choice.label }}</label
            >
          </div>
        </div>
      </div>
    </div>
    <div
      v-show="
        step === STEP_MESSAGE_COST_UPDATE ||
        (isDesktop &&
          (step === STEP_MESSAGE_COST_CHECK_ANY ||
            step === STEP_MESSAGE_COST_CHECK_LAST) &&
          formDoUpdateCost)
      "
      class="container"
    >
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
                }"
              />
              <span class="input-group-text">Euro</span>
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
          <!-- TODO: if we expect users to go back a lot, the document-uploader list
                shown here should exclude/disable "has schwärzung" docs -->
          <p>
            {{ i18n.redactionInfo }}
          </p>
          <div class="text-end">
            <button
              type="button"
              class="btn btn-link mx-2 text-decoration-underline"
              @click="documentUploaderSelectAll(true)"
            >
              {{ i18n.selectAll }}
            </button>
            <button
              type="button"
              class="btn btn-link mx-2 text-decoration-underline"
              @click="documentUploaderSelectAll(false)"
            >
              {{ i18n.selectNone }}
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
                  total: documentsSelectedPdfRedaction.length
                })
              }}
            </label>
            <div class="alert alert-warning">
              {{ i18n.redactionInfoWhat }}
              <ul>
                <li>
                  {{ i18n.redactionInfoWhat1 }}
                </li>
                <li>
                  {{ i18n.redactionInfoWhat2 }}
                </li>
                <li>
                  {{ i18n.redactionInfoWhat3 }}
                </li>
                <li>
                  {{ i18n.redactionInfoWhat4 }}
                </li>
              </ul>
            </div>
            <div class="mt-2 mb-3">
              <button
                type="button"
                class="btn btn-link text-decoration-underline"
                @click="onlineHelp.show(config.urls.helpPostuploadRedaction)"
              >
                {{ i18n.helpNeeded }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div>
        <div class="debug" v-if="debug">
          DEBUG: pdfRedactionCurrentIndex= {{ pdfRedactionCurrentIndex }}<br />
          auto_approve current = {{ pdfRedactionCurrentDoc?.auto_approve }}
        </div>
        <pdf-redaction
          v-if="pdfRedactionCurrentDoc"
          :key="pdfRedactionCurrentDoc.id"
          :pdf-path="pdfRedactionCurrentDoc.attachment.file_url"
          :attachment-url="pdfRedactionCurrentDoc.attachment.anchor_url"
          :auto-approve="pdfRedactionCurrentDoc.auto_approve"
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
          :minimal-ui="true"
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
        </div>
      </div>
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
    <!-- not in v-show="step ..." -->
    <div v-show="stepContext.documents">
      <div class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div
              v-if="step === STEP_DOCUMENTS_OVERVIEW_REDACTED && !user_is_staff"
              class="d-flex justify-content-end"
            >
              <button
                type="button"
                class="btn btn-link text-decoration-underline"
                @click="documentsBasicOperations = !doctumentsBasicOperations"
              >
                {{ documentsBasicOperations ? i18n.done : i18n.edit }}
              </button>
            </div>
            <!-- TODO maybe :hide-documents (PDFs) in step STEP_DOCUMENTS_UPLOAD -->
             DOCUMENT UPLOADER
            <document-uploader
              :debug="debug"
              :config="config"
              :message="draft"
              :show-upload="stepContext.documentsUpload"
              :icon-style="stepContext.documentsIconStyle"
              :show-auto-approve="stepContext.documentsShowAutoApprove"
              :hide-selection="stepContext.documentsHideSelection"
              :hide-selection-bar="true"
              :hide-other="true"
              :hide-pdf="stepContext.documentsHidePdf"
              :hide-status-tools="true"
              :images-simple="stepContext.documentsImagesSimple"
              :images-document-filename="
                documentsImagesDocumentFilenameNormalized
              "
              :file-basic-operations="
                step === STEP_DOCUMENTS_OVERVIEW || documentsBasicOperations
              "
              :hide-advanced-operations="true || !(debug && user_is_staff)"
              :highlight-redactions="stepContext.documentsHighlightRedactions"
              @selectionupdated="documentsSelectedPdfRedaction = $event"
              @imagesadded="documentsImagesAdded"
              @documentsadded="documentsDocumentsAdded"
              @imagesconverted="documentsImagesConverted"
              ref="documentUploader"
            >
              <template #fileuploader-after>
                <div class="form-text text-center">{{  i18n.scanHelpText }}</div>
              </template>
            </document-uploader>
          </div>
        </div>
      </div>
    </div>
    <div v-show="step === STEP_DOCUMENTS_OVERVIEW" class="container">
      <div class="row justify-content-center">
        <div class="col-sm-9 col-md-6 mt-3">
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100 mb-3"
            :disabled="true"
          >
            <i class="fa fa-plus"></i>
            {{ i18n.scanDocumentsAnother }}
          </button>
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100"
            @click="gotoStep(STEP_DOCUMENTS_UPLOAD)"
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
              @click="approveAndSubmit()"
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
            <button
              type="button"
              @click="submitForm"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.requestShow }}
            </button>
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
          </template>
          <template v-else-if="step === STEP_DOCUMENTS_UPLOAD">
            <!-- this could be completely hidden -->
            <button
              type="button"
              :disabled="true"
              class="btn btn-primary d-block w-100"
            >
              {{ i18n.next }}
            </button>
            <button
              v-if="debug"
              type="button"
              @click="gotoStep()"
              class="action btn btn-outline-primary btn-sm mt-1"
            >
              DEBUG skip
            </button>
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
              v-if="documentUploader.$refs.imageDocument.length > 0"
              type="button"
              @click="documentsConvertImages"
              class="btn btn-primary d-block w-100"
              :disabled="documentsImagesConverting"
            >
              <span
                class="spinner-border spinner-border-sm"
                v-if="documentsImagesConverting"
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
</style>
