<script setup>
import { ref, reactive, computed, defineProps, nextTick, watch } from 'vue'
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
import { Tooltip } from 'bootstrap'
import { useI18n } from '../../lib/i18n'

/* DEBUG
const delay = function (duration) {
  return function (x) {
    return new Promise((resolve) => {
      console.info('delaying', duration, resolve)
      setTimeout(function () {
        console.log('delay done')
        resolve(x)
      }, duration)
    })
  }
}
*/

// this could possibly move to lib/vue-helper.ts
const vBsTooltip = {
  mounted: (el) => {
    new Tooltip(el)
  }
}

const props = defineProps({
  config: Object,
  form: Object,
  message: Object,
  status_form: Object,
  object_public_body_id: String,
  object_public_body: Object,
  object_public: Boolean,
  date_min: String,
  date_max: String,
  user_is_staff: Boolean
})

const { i18n } = useI18n(props.config)

const debug = ref(!!localStorage.getItem('fds-postupload-debug'))
window.FDSdebug = (val) => {
  debug.value = typeof val === 'boolean' ? val : !debug.value
  localStorage.setItem('fds-postupload-debug', debug.value ? 'yes' : '')
}

const isDesktop = ref(false)
const updateIsDesktop = (mql) => {
  isDesktop.value = mql.matches
}
const froideAppshellBreakpoint = getComputedStyle(
  document.body
).getPropertyValue('--froide-appshell-breakpoint')
const isDesktopMediaQueryList = window.matchMedia(
  `(min-width: ${froideAppshellBreakpoint})`
)
updateIsDesktop(isDesktopMediaQueryList)
isDesktopMediaQueryList.addEventListener('change', updateIsDesktop)

const beforeunloadHandler = (e) => e.preventDefault()
let isBeforeunloadGuarded = false
const guardBeforeunload = (enable) => {
  if (enable) {
    if (!isBeforeunloadGuarded) {
      window.addEventListener('beforeunload', beforeunloadHandler)
      isBeforeunloadGuarded = true
    }
  } else {
    window.removeEventListener('beforeunload', beforeunloadHandler)
  }
}

const firstStep = 1100

/*
// This naive implementation of a hash-router for steps works
// - back button works as intended
// - load into any step, too
// but
// - there are timing issues, i.e. uppyClick doesn't really fire - probably due to nextTick not waiting long enough for the hashchange to settle
// - going history.back arbitrarily breaks state in subtle ways, i.e. when going from 1202 to 1201
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
    return 1100
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

const stepHistory = reactive([firstStep])
const step = computed(() => 
  stepHistory.length ? stepHistory[stepHistory.length - 1] : false
)

const gotoStep = (nextStep) => {
  nextStep = nextStep || getNextStep()
  // document.location.href = '#' + nextStep
  stepHistory.push(nextStep)
}

/* untangle ambiguous semantics:
 * there is message.sent, but this is not the same.
 * sent in the Form's context means "negated is_response"
 * TODO: this should be cleaned up at the model level.
 */
const formSent = ref(
  props.message?.is_response ? '0' : '1'
)
const formIsSent = computed(() => formSent.value === '1')

const formPublicbodyIsDefault = ref(true)

const formStatus = ref(
  props.status_form.fields.status.value ||
    props.status_form.fields.status.initial
)
const formStatusWasResolved = formStatus.value === 'resolved'
const formStatusIsResolved = computed(() => formStatus.value === 'resolved')

// remove nonsensical combos
const formStatusChoices = computed(() => {
  const badCombinations = formIsSent.value
    ? ['', 'successful', 'partially_successful', 'not_held', 'refused']
    : ['user_withdrew_costs']
  return props.status_form.fields.resolution.choices.filter(
    (choice) => !badCombinations.includes(choice.value)
  )
})

const formCost = props.status_form.fields.costs.initial?.intValue || 0
const formHasHadCost = formCost > 0
const formDoUpdateCost = ref(false)

const formPublicbodyId =
  props.form.fields.publicbody.value ||
  props.form.fields.publicbody?.initial?.id?.toString() ||
  props.object_public_body_id

const formPublicbodyLabel = props.object_public_body?.name || 'Error'

const documentsSelectedPdfRedaction = ref([])
const documentsPdfRedactionIndex = computed(() => {
  if (3000 < step.value && step.value < 3100) return step.value - 3001
  return false
})

const currentPdfRedactionDoc = computed(() => {
  if (documentsPdfRedactionIndex.value === false) return
  return documentsSelectedPdfRedaction.value[documentsPdfRedactionIndex.value]
})

const documentUploader = ref()
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
const documentsImagesDocumentFilenameDefault = 'brief.pdf'
const documentsImagesDocumentFilename = ref(
  documentsImagesDocumentFilenameDefault
)
const documentsImagesDocumentFilenameNormalized = computed(() =>
  documentsImagesDocumentFilename.value.replace(/\.pdf$/, '')
)

const documentsBasicOperations = ref(false)

const pdfRedaction = ref()
const pdfRedactionCurrentHasRedactions = ref(false)
const pdfRedactionProcessing = ref(false)
const pdfRedactionRedact = () => {
  pdfRedactionProcessing.value = true
  // XXX calling child's method
  // alternatively, could listen to an event
  pdfRedaction.value
    .redactOrApprove()
    // .then(delay(3000))
    .then(() => {
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

const documentUploaderSelectAll = (val) => {
  documentUploader.value.setAllSelect(val)
}

const scrollIfNecessary = () => {
  const header = document.querySelector('main nav')
  const rect = header.getBoundingClientRect()
  if (rect.bottom < 0) {
    // timeout to make it feel less jarring
    setTimeout(() => header.scrollIntoView({ behavior: 'smooth' }), 500)
  }
}

const mobileHeaderTitle2 = computed(() => {
  switch (step.value) {
    case 1100:
      return i18n.value.addLetter
    case 4570:
      return 'Fertig'
  }
  if (step.value < 2000) {
    return 'Brief hochladen oder scannen'
  }
  if (2000 <= step.value && step.value < 3000) {
    return 'Infos eingeben'
  }
  if (3000 <= step.value && step.value < 4000) {
    return 'Schwärzen'
  }
  if (step.value >= 4000) {
    return 'Vorschau'
  }
  return '(Untertitel)'
})

const progressStep = computed(() =>
  // map to {0, 1, 2}
  Math.min(Math.floor((step.value - 1000) / 1000), 2)
)

const gotoValid = computed(() => {
  if (
    step.value === 2565 ||
    (isDesktop.value &&
      (step.value === 2388 || step.value === 2390) &&
      formDoUpdateCost.value)
  ) {
    return validity.costs
  }
  if (isDesktop.value && step.value === 2384 && values.is_registered_mail) {
    return validity.date && validity.registered_mail_date
  }
  if (step.value === 2382) {
    return validity.registered_mail_date
  }
  if (step.value === 2384) {
    return validity.date
  }
  return true
})

const backStep = () => {
  if (step.value === 1201) {
    // we go back two steps
    stepHistory.pop()
    // history.back()
  }
  stepHistory.pop()
  // history.back()
}

const isSubmitting = ref(false)

const submit = async () => {
  document.forms.postupload.submit()
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
      if (!response.ok) throw new Error('form submit error')
      return response.json()
    })
    .then((response) => {
      isSubmitting.value = false
      if ('errors' in response) {
        console.error('fetch submit errors', response.errors)
        // TODO handle this better: at least use a proper modal,
        // better: link to steps which are wrong?
        // like: if 'date' in errors link to step with <input type=date>
        alert('errors: ' + JSON.stringify(response.errors, false, 2))
        return
      }
    })
}

const approveDocsAndSubmit = async () => {
  isSubmitting.value = true
  try {
    // unnecessary since redacted documents are auto-approved
    // and staff users will ... be handled differently? TODO
    // await approveDocs()
    await submitFetch()
    gotoStep()
  } catch (err) {
    console.error('fetch submit error', err)
    alert('error' + JSON.stringify(err))
  } finally {
    isSubmitting.value = false
  }
}

// TODO WIP numbers from Figma frames
const getNextStep = () => {
  switch (step.value) {
    case 1100:
      return 1110
    case 1110:
      if (documentsImageMode.value) {
        console.log(
          'uploads were documents, not images, passing by image sorting'
        )
        return 1201
      }
      return 2376
    case 1201:
      return 1202
    case 1202:
      return 1300
    case 1300:
      return 2376
    case 2376:
      return 2380
    case 2380:
      if (isDesktop.value) return 2384
      return formPublicbodyIsDefault.value ? 2384 : 2381
    case 2381:
      return 2384
    case 2384:
      if (isDesktop.value) return 2437
      return values.is_registered_mail ? 2382 : 2437
    case 2382:
      return 2437
    case 2437:
      if (!isDesktop.value && formStatusIsResolved.value) return 2438
      // TODO: replace all 3402 with `if uploadedDocuments.length === 1 ? ... : 3402`
      if (formIsSent.value) return 3402
      return formHasHadCost ? 2390 : 2388
    case 2438:
      if (formIsSent.value) return 3402
      return formHasHadCost ? 2390 : 2388
    case 2388:
    case 2390:
      if (formDoUpdateCost.value) return 2565
      return 3402
    case 2565:
      return 3402
    case 3402:
      if (documentsSelectedPdfRedaction.value.length === 0) return 4413
      return 3001 // TODO
    /*
    case 3001:
      if (
        documentsPdfRedactionIndex.value <
        documentsSelectedPdfRedaction.value.length - 1
      ) {
        documentsPdfRedactionIndex.value++
        return 3001
      }
      return 4413
    */
    case 4413:
      return 4570
    case 4570:
      return 4570
  }
  if (3000 < step.value && step.value < 3100) {
    if (
      documentsPdfRedactionIndex.value <
      documentsSelectedPdfRedaction.value.length - 1
    ) {
      return step.value + 1
    }
    return 4413
  }
}

// side effects for (entering) steps
watch(step, (newStep) => {
  console.log('# watch step', newStep)
  switch (newStep) {
    case 1110:
      guardBeforeunload(true)
      documentsImagesDocumentFilename.value =
        documentsImagesDocumentFilenameDefault
      break
    case 1300:
      pdfRedactionUploaded()
      break
    case 2382:
      updateValidity('date')
      updateValidity('registered_mail_date')
      break
    case 2384:
      updateValidity('date')
      updateValidity('registered_mail_date')
      break
    case 2565:
      updateValidity('costs')
      break
    case 3402:
      pdfRedactionUploaded()
      break
    case 4413:
      documentsBasicOperations.value = false
      updateValidity('form')
      pdfRedactionUploaded()
      break
    case 4570:
      guardBeforeunload(false)
  }
  scrollIfNecessary()
})

const stepUiConf = {
  1110: {
    documents: true,
    documentsUpload: true,
    documentsHideSelection: true,
    documentsHidePdf: true,
    documentsImagesSimple: true
  },
  1201: {
    documents: true,
    documentsUpload: true,
    documentsHideSelection: true,
    documentsHidePdf: true,
    documentsImagesSimple: true
  },
  1300: {
    documents: true,
    documentsUpload: false,
    documentsHideSelection: true,
    // would make sense "if has geschwärzte docs", i.e. when we expect users to go back
    // documentsHighlightRedactions: true,
    documentsIconStyle: 'icon'
  },
  3402: {
    documents: true,
    documentsIconStyle: 'thumbnail'
  },
  4413: {
    documents: true,
    documentsHideSelection: true, // !(props.object_public && props.user_is_staff),
    documentsIconStyle: 'thumbnail',
    documentsHighlightRedactions: true
  }
}

const uiDocuments = computed(() => stepUiConf[step.value]?.documents || false)
const uiDocumentsUpload = computed(
  () => stepUiConf[step.value]?.documentsUpload || false
)
const uiDocumentsHideSelection = computed(
  () => stepUiConf[step.value]?.documentsHideSelection || false
)
const uiDocumentsHidePdf = computed(
  () => stepUiConf[step.value]?.documentsHidePdf || false
)
const uiDocumentsIconStyle = computed(
  () => stepUiConf[step.value]?.documentsIconStyle || ''
)
const uiDocumentsImagesSimple = computed(
  () => stepUiConf[step.value]?.documentsImagesSimple || false
)
const uiDocumentsHighlightRedactions = computed(
  () => stepUiConf[step.value]?.documentsHighlightRedactions || false
)

const documentsImageMode = ref(false)
const documentsImagesAdded = () => {
  if (step.value !== 1110) {
    return
  }
  documentsImageMode.value = true
  gotoStep()
}
const documentsDocumentsAdded = () => {
  if (step.value !== 1110) {
    return
  }
  gotoStep()
}
const documentsImagesConverted = () => {
  documentsImagesConverting.value = false
  if (step.value !== 1202) {
    console.warn("conversion shouldn't have happened here")
    return
  }
  gotoStep()
}

const validity = reactive({
  date: false,
  registered_mail_date: false
})

// TODO updateValidity should (maybe) be called on gotoStep(2384), too
const updateValidity = (key) => {
  const el =
    key === 'form'
      ? document.forms.postupload
      : document.forms.postupload.elements[key]
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
  // console.log('updateValidity', el, 'value=', el.value, 'checkValidity()', el.checkValidity(), validity[key], validity, values)
  /*
  console.log(
    'updateValidity',
    el,
    JSON.stringify({
      value: el.value,
      'checkValidity()': el.checkValidity(),
      'validity[key]': validity[key],
      validity,
      values
    })
  )
  */
}

const values = reactive({
  // FIXME date doesn't populate from a saved form?
  date: props.form.fields.date.value,
  registered_mail_date: props.form.fields.registered_mail_date.value,
  costs:
    props.status_form.fields.costs.value?.strValue ||
    props.status_form.fields.costs.initial.strValue,
  is_registered_mail: false
})

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

const debugSkipDate = () => {
  values.date = document.forms.postupload.elements.date.max
  values.registered_mail_date = document.forms.postupload.elements.date.max
  updateValidity('date')
  updateValidity('registered_mail_date')
  gotoStep()
}

const onlineHelp = ref()
</script>

<template>
  <online-help ref="onlineHelp" />
  <div class="root">
    <div class="postupload-main">
      <simple-stepper
        class="sticky-top position-md-static"
        :step="progressStep"
        :steps="['Hochladen', 'Infos eingeben', 'Schwärzen']">
        <template v-if="step < 4000">
          {{ i18n.step }} {{ Math.floor(step / 1000) }}<strong>/3</strong>:
          {{ mobileHeaderTitle2 }}
        </template>
        <template v-else-if="step >= 4000">
          <small>{{ i18n.done }}</small>
        </template>
      </simple-stepper>

      <div class="container">
        <!-- TODO button does not support going back throug documentsPdfRedactionIndex -->
        <div v-if="step === 1100" class="my-3">
          <a class="btn btn-link text-decoration-none ps-0" href="../.."
            >← <u>{{ i18n.cancel }}</u></a
          >
        </div>
        <div v-else-if="step !== 4570" class="my-3">
          <a @click="backStep" class="btn btn-link text-decoration-none ps-0"
            >← <u>{{ i18n.back }}</u></a
          >
        </div>
      </div>

      <details v-if="debug" class="container">
        <summary class="DEBUG">DEBUG</summary>
        <div>step={{ step }}</div>
        <div>history={{ stepHistory.join(',') }}</div>
        <span>
          <!-- eslint-disable-next-line vue/no-mutating-props -->
          <button type="button" @click="user_is_staff = !user_is_staff">
            {{ user_is_staff ? '☑' : '☐' }} staff
          </button>
        </span>
        <span>isDesktop={{ isDesktop }}</span>
        <button
          class="btn btn-secondary btn-sm"
          type="submit"
          style="font-size: 50%; margin-left: 1em">
          submit/save
        </button>
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          @click="submitFetch"
          style="font-size: 50%; margin-left: 1em">
          submit/fetch
        </button>
        <!--<pre>{{ validity }}</pre>-->
        <!-- <span v-if="debug" class="debug">desktop={{ isDesktop }},</span> -->
        <!--<span class="debug">{{ stepHistory.join(',') }}</span>-->
        <!--<span class="debug">p{{ progress }}</span>-->
        <!--<small>{{ { uiDocuments, uiDocumentsUpload } }}</small>-->
        <!--<span class="debug">{{ values.isYellow }}</span>-->
        <!--<span class="debug">{{ gotoValid }}</span>-->
        <!--<span class="debug">
          {{ { pbv: props.form.fields.publicbody.value, pbii:  props.form.fields.publicbody?.initial?.id, opbi: object_public_body_id } }}
        </span>-->
        <!-- <span class="debug">formStatus={{formStatus}},</span> -->
        <!-- <span class="debug">formDoUpdateCost={{formDoUpdateCost}},</span> -->
        <!--<span class="debug">{{documentsSelectedPdfRedaction}}</span>-->
        <!--<span class="debug">documentsSelectedPdfRedaction={{ documentsSelectedPdfRedaction.map(d => d.id).join(',') }}</span>-->
        <details v-if="form.nonFieldErrors.length">
          <summary class="debug">DEBUG form.nonFieldErrors</summary>
          <pre>{{ form.nonFieldErrors }}</pre>
        </details>
        <details v-if="Object.keys(form.errors).length">
          <summary class="debug">DEBUG form.errors</summary>
          <pre>{{ form.errors }}</pre>
        </details>
      </details>

      <div v-show="step === 1100" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="row my-5">
              <div class="col-md-6">
                <button disabled class="btn btn-outline-primary d-block w-100">
                  <i class="fa fa-camera"></i>
                  Dokumente scannen
                </button>
                <p class="mt-1">
                  Handykamera verwenden, um automatisch ein PDF zu erstellen
                </p>
              </div>
              <div class="col-md-6">
                <button
                  type="button"
                  @click="stepAndUppyClick"
                  class="btn btn-outline-primary d-block w-100">
                  <i class="fa fa-upload"></i>
                  Dateien hochladen
                </button>
                <p class="mt-1">
                  Wenn Sie den Brief schon als PDF oder Foto vorliegen haben
                </p>
              </div>
            </div>
            <div class="alert alert-warning">
              <h4><i class="fa fa-lightbulb-o fa-lg"></i> Tipp</h4>
              <p>
                Sie brauchen den Brief vorher <strong>nicht</strong> zu
                schwärzen. Das erledigen Sie später mit unserem Online-Tool.
              </p>
              <p>Wir führen Sie Schritt für Schritt durch den Prozess.</p>
              <p>
                <a @click="onlineHelp.show(config.urls.helpPostuploadRedaction)"
                  >online help demo</a
                >
              </p>
            </div>
            <div class="alert alert-warning">
              <h4><i class="fa fa-exclamation-circle fa-lg"></i> Neu</h4>
              <p>Wir haben diesen Bereich stark überarbeitet.</p>
              <p>
                Sollte etwas nicht funktionieren, gibt es
                <a :href="config.url.legacyPostupload"
                  >hier noch das alte Upload-Formular</a
                >. Wir würden uns über Feedback freuen.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 1110">
        <!-- document-uploader see below -->
      </div>

      <div v-show="step === 1201" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9 fw-bold">
            Ziehen Sie die Seiten in die richtige Reihenfolge
          </div>
        </div>
      </div>

      <div v-show="step === 1202" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="text-center my-3">
              <i class="fa fa-file-image-o fa-4x"></i>
              <i class="fa fa-arrow-right fa-2x"></i>
              <i class="fa fa-file-pdf-o fa-4x"></i>
            </div>
          </div>
          <div class="text-center fw-bold my-3">
            Wir erstellen aus Ihren Bildern ein PDF-Dokument
          </div>
          <div class="documents-filename p-2 my-3 mx-auto">
            <div class="form-group">
              <input
                id="documents_filename"
                v-model="documentsImagesDocumentFilename"
                class="form-control" />
              <label for="documents_filename"> Dateiname ändern </label>
            </div>
          </div>
        </div>
      </div>

      <!-- there is another for this step, further down below document-uploader -->
      <div v-show="step === 1300" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="fw-bold">Bisher vorhandene Dokumente</div>
          </div>
        </div>
      </div>

      <div v-show="step === 2376" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 1 von 5</div>
            <label class="fw-bold form-label">
              Haben Sie den hochgeladenen Brief erhalten oder versendet?
              <!--{{ form.fields.sent.label }}-->
            </label>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in form.fields.sent.choices"
              :key="choice.value"
              :class="{ 'is-invalid': choice.errors }">
              <input
                type="radio"
                name="sent"
                v-model="formSent"
                required=""
                class="form-check-input"
                :id="'id_sent_' + choiceIndex"
                :value="choice.value" />
              <label class="form-check-label" :for="'id_sent_' + choiceIndex">{{
                choice.label
              }}</label>
            </div>
            <!--
            <div class="invalid-feedback" v-if="form.errors.sent">
              <p class="text-danger">
                {{ form.errors.sent.map((_) => _.message).join(' ') }}
              </p>
            </div>
            -->
          </div>
        </div>
      </div>

      <!-- also 2428 -->
      <div v-show="step === 2380" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 2 von 5</div>
            <label class="fw-bold form-label" for="id_subject">
              <template v-if="formSent === '1'">
                Ist dies die Behörde, an die Sie den Brief gesendet haben?
              </template>
              <template v-else>
                Ist dies die Behörde, von der der Brief stammt?
              </template>
            </label>
            <div style="margin: 1em 0; font-style: italic">
              {{ formPublicbodyLabel }}
            </div>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in [
                { value: true, label: 'Ja.' },
                { value: false, label: 'Nein, andere Behörde wählen' }
              ]"
              :key="choiceIndex">
              <input
                type="radio"
                required=""
                class="form-check-input"
                v-model="formPublicbodyIsDefault"
                :id="'id_pbisdefault_' + choiceIndex"
                :value="choice.value" />
              <label
                class="form-check-label"
                :for="'id_pbisdefault_' + choiceIndex"
                >{{ choice.label }}</label
              >
            </div>
            <input
              type="hidden"
              name="publicbody"
              v-if="formPublicbodyIsDefault"
              :value="formPublicbodyId" />
          </div>
        </div>
      </div>

      <div
        v-show="
          step === 2381 ||
          (isDesktop && step === 2380 && !formPublicbodyIsDefault)
        "
        class="container">
        <!-- appears "indented" on md=isDesktop viewport -->
        <div class="row justify-content-center">
          <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
            <!-- also 2429 -->
            <label class="fw-bold form-label" for="id_subject">
              <template v-if="formSent === '1'">
                An welche Behörde haben Sie den Brief gesendet?
              </template>
              <template v-else>
                Von welcher Behörde stammt der Brief?
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
              :class="{ 'is-invalid': form.errors.publicbody }" />
          </div>
        </div>
      </div>

      <div v-show="step === 2384" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 3 von 5</div>
            <label class="fw-bold form-label field-required" for="id_date">
              Wann wurde der Brief versendet?
              <!--{{ form.fields.date.label }}-->
            </label>
            <!-- has to be @required "one too early" so checkValidity doesn't return true when empty on enter step -->
            <!-- TODO "always" required might break early post/submit
              :required="step === 2384 || step === 2380"
              maybe: step > 2380 ?
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
              @input="updateValidity('date')" />
            <div class="invalid-feedback" v-if="form.errors.date">
              <p class="text-danger">
                {{ form.errors.date.map((_) => _.message).join(' ') }}
              </p>
            </div>
            <div class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="values.is_registered_mail"
                id="id_is_registered_mail" />
              <label class="form-check-label" for="id_is_registered_mail">
                Es handelt sich um einen gelben Brief
                <span
                  type="button"
                  v-bs-tooltip
                  tabindex="0"
                  data-bs-toggle="tooltip"
                  data-bs-placement="bottom"
                  title="Ein gelber Brief ist eine förmliche Zustellung mit Zustellungsurkunde. Normalerweise befindet sich solch ein Brief in einem gelben Umschlag, aber es gibt auch Ausnahmen.">
                  <i class="fa fa-info-circle"></i>
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div
        v-show="
          step === 2382 ||
          (isDesktop && step === 2384 && values.is_registered_mail)
        "
        class="container">
        <div class="row justify-content-center">
          <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
            <label
              class="fw-bold form-label field-required"
              for="id_registered_mail">
              Gelber Brief: Welches Zustelldatum wurde auf dem Briefumschlag
              eingetragen?
            </label>
            <!-- TODO set min/max? -->
            <input
              type="date"
              class="form-control"
              id="id_registered_mail_date"
              name="registered_mail_date"
              :required="values.is_registered_mail"
              @input="updateValidity('registered_mail_date')"
              v-model="values.registered_mail_date" />
          </div>
        </div>
      </div>

      <!-- also 2386,2435,2440 -->
      <div v-show="step === 2437" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 4 von 5</div>
            <label class="fw-bold form-label" for="id_subject">
              <template v-if="!formIsSent && formStatusWasResolved">
                Ihre Anfrage war bereits abgeschlossen. Ist dies nach Erhalt des
                Briefes immer noch der Fall?
              </template>
              <template v-if="!formIsSent && !formStatusWasResolved">
                Wurde ihre Anfrage durch Erhalt dieses Briefes abgeschlossen?
              </template>
              <template v-if="formIsSent && formStatusWasResolved">
                Ihre Anfrage war bereits abgeschlossen. Ist dies nach Versenden
                des Briefes noch immer der Fall?
              </template>
              <template v-if="formIsSent && !formStatusWasResolved">
                Wurde Ihre Anfrage durch Versenden dieses Briefes abgeschlossen?
              </template>
            </label>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in status_form.fields.status.choices"
              :key="choice.value">
              <input
                type="radio"
                name="status"
                required=""
                class="form-check-input"
                :class="{ 'is-invalid': choice.errors }"
                :id="'id_status_' + choiceIndex"
                v-model="formStatus"
                :value="choice.value"
                :data-x-checked="formStatus.value === choice.value" />
              <label class="form-check-label" :for="'id_status_' + choiceIndex">
                <template v-if="formStatusWasResolved">
                  <template v-if="choice.value === 'resolved'">
                    Meine Anfrage ist nach wie vor abgeschlossen.
                  </template>
                  <template v-else> Meine Anfrage läuft nun wieder. </template>
                </template>
                <template v-else>
                  <template v-if="choice.value === 'resolved'">
                    Ja, Anfrage ist jetzt abgeschlossen.
                  </template>
                  <template v-else> Nein, Anfrage läuft noch. </template>
                </template>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- also 2387,2436,2439 -->
      <div
        v-show="
          step === 2438 || (isDesktop && step === 2437 && formStatusIsResolved)
        "
        class="container">
        <div class="row justify-content-center">
          <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
            <label class="fw-bold col-form-label" for="id_resolution">
              <!-- {{ status_form.fields.resolution.label }} -->
              Wie würde Sie das Ergebnis beschreiben?
            </label>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in formStatusChoices"
              :key="choice.value">
              <input
                type="radio"
                name="resolution"
                :required="formStatusIsResolved"
                class="form-check-input"
                :id="'id_resolution_' + choiceIndex"
                :value="choice.value"
                :checked="
                  status_form.fields.resolution.value === choice.value ||
                  status_form.fields.resolution.initial === choice.value
                " />
              <label
                class="form-check-label"
                :for="'id_resolution_' + choiceIndex"
                >{{ choice.label }}</label
              >
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 2388" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 5 von 5</div>
            <label class="fw-bold col-form-label">
              Hat die Behörde Kosten verlangt?
            </label>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in [
                { label: 'Nein.', value: false },
                { label: 'Ja.', value: true }
              ]"
              :key="choiceIndex">
              <input
                type="radio"
                required=""
                class="form-check-input"
                v-model="formDoUpdateCost"
                :id="'id_nowcost_' + choiceIndex"
                :value="choice.value" />
              <label
                class="form-check-label"
                :for="'id_nowcost_' + choiceIndex"
                >{{ choice.label }}</label
              >
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 2390" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="step-questioncounter">Frage 5 von 5</div>
            <label class="fw-bold col-form-label" for="id_nowcost">
              Sie hatten bereits mitgeteilt, dass die Behörde Kosten in Höhe von
              {{
                status_form.fields.costs.value?.strValue ||
                status_form.fields.costs.initial?.strValue ||
                'error'
              }}€ verlangt hat.<br />
              Ist dieser Betrag noch korrekt?
            </label>
            <div
              class="form-check"
              v-for="(choice, choiceIndex) in [
                { label: 'Ja.', value: false },
                { label: 'Nein.', value: true }
              ]"
              :key="choiceIndex">
              <input
                type="radio"
                required=""
                class="form-check-input"
                v-model="formDoUpdateCost"
                :id="'id_nowcost_' + choiceIndex"
                :value="choice.value" />
              <label
                class="form-check-label"
                :for="'id_nowcost_' + choiceIndex"
                >{{ choice.label }}</label
              >
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 3402" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <label class="fw-bold col-form-label">
              Welche dieser Dokumente möchen Sie schwärzen?
            </label>
            <!-- TODO: if we expect users to go back a lot, the document-uploader list
              shown here should exclude/disable "has schwärzung" docs -->
            <p>
              Ein Dokument sollte geschwärzt werden, wenn es personenbezogene
              Informationen über Sie selbst oder Behördenmitarbeiter:innen
              enthält.
            </p>
            <div class="text-end">
              <button
                type="button"
                class="btn btn-link mx-2 text-decoration-underline"
                @click="documentUploaderSelectAll(true)">
                Alle auswählen
              </button>
              <button
                type="button"
                class="btn btn-link mx-2 text-decoration-underline"
                @click="documentUploaderSelectAll(false)">
                Keine auswählen
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-show="3000 < step && step < 3100">
        <div class="container">
          <div class="row">
            <div class="col">
              <label class="fw-bold col-form-label">
                Dokument schwärzen ({{ documentsPdfRedactionIndex + 1 }} von
                {{ documentsSelectedPdfRedaction.length }})
              </label>
              <div class="alert alert-warning">
                Das sollten Sie schwärzen:
                <ul>
                  <li>Ihren Namen und Ihre Adresse</li>
                  <li>Namen von Behördenmitarbeiter:innen</li>
                  <li>Unterschriften</li>
                  <li>E-Mail-Adressen, die auf ‘@fragdenstaat.de’ enden</li>
                </ul>
              </div>
              <div class="mt-2 mb-3">
                <button
                  type="button"
                  class="btn btn-link text-decoration-underline"
                  @click="onlineHelp.show(config.urls.helpPostuploadRedaction)">
                  Ich habe technische Probleme / benötige Hilfe
                </button>
              </div>
            </div>
          </div>
        </div>
        <div>
          <pre class="debug" v-if="debug">
    DEBUG: documentsPdfRedactionIndex = {{ documentsPdfRedactionIndex }}</pre
          >
          <pdf-redaction
            v-if="currentPdfRedactionDoc"
            :key="currentPdfRedactionDoc.id"
            :pdf-path="currentPdfRedactionDoc.attachment.file_url"
            :attachment-url="currentPdfRedactionDoc.attachment.anchor_url"
            :post-url="
              config.url.redactAttachment.replace(
                '/0/',
                '/' + currentPdfRedactionDoc.id + '/'
              )
            "
            :approve-url="
              config.url.approveAttachment.replace(
                '/0/',
                '/' + currentPdfRedactionDoc.id + '/'
              )
            "
            :minimal-ui="true"
            :no-redirect="true"
            :redact-regex="['teststraße\ 1']"
            :can-publish="true"
            :config="config"
            @uploaded="pdfRedactionUploaded"
            @hasredactionsupdate="pdfRedactionCurrentHasRedactions = $event"
            ref="pdfRedaction">
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
          </pdf-redaction>
        </div>
      </div>

      <div v-show="step === 4413" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9">
            <div class="fw-bold col-form-label">
              Diese Dokumente werden der Anfrage hinzugefügt:
            </div>
          </div>
        </div>
      </div>

      <div
        v-show="
          step === 2565 ||
          (isDesktop && (step === 2388 || step === 2390) && formDoUpdateCost)
        "
        class="container">
        <div class="row justify-content-center">
          <div class="col-md-11 offset-md-1 col-lg-8 mt-md-5">
            <label class="fw-bold col-form-label" for="id_costs">
              Welchen Betrag hat die Behörde verlangt?
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
                <span class="input-group-text">Euro</span>
              </div>
              <!--<div class="form-text">{{ status_form.fields.costs.help_text }}</div>-->
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 4570" class="container">
        <div class="row justify-content-center">
          <div class="col-lg-9 text-center">
            <div class="my-3">
              <i class="fa fa-check-square fa-4x"></i>
            </div>
            <div class="fw-bold col-form-label">
              Dokumente erfolgreich hinzugefügt
            </div>
            <div>
              Danke, dass Sie Ihre Anfrage auf den neuesten Stand gebracht
              haben!
            </div>
          </div>
        </div>
      </div>

      <!-- not in v-show="step ..." -->
      <div v-show="uiDocuments">
        <div class="container">
          <div class="row justify-content-center">
            <div class="col-lg-9">
              <div
                v-if="step === 4413 && !user_is_staff"
                class="d-flex justify-content-end">
                <button
                  type="button"
                  class="btn btn-link text-decoration-underline"
                  @click="
                    documentsBasicOperations = !doctumentsBasicOperations
                  ">
                  {{ documentsBasicOperations ? 'Fertig' : 'Bearbeiten' }}
                </button>
              </div>
              <!-- TODO maybe :hide-documents (PDFs) in step 1110 -->
              <document-uploader
                :debug="debug"
                :config="config"
                :message="message"
                :show-upload="uiDocumentsUpload"
                :icon-style="uiDocumentsIconStyle"
                :hide-selection="uiDocumentsHideSelection"
                :hide-selection-bar="true"
                :hide-other="true"
                :hide-pdf="uiDocumentsHidePdf"
                :hide-status-tools="true"
                :images-simple="uiDocumentsImagesSimple"
                :images-document-filename="
                  documentsImagesDocumentFilenameNormalized
                "
                :file-basic-operations="
                  step === 1300 || documentsBasicOperations
                "
                :hide-advanced-operations="true || !(debug && user_is_staff)"
                :highlight-redactions="uiDocumentsHighlightRedactions"
                @selectionupdated="documentsSelectedPdfRedaction = $event"
                @imagesadded="documentsImagesAdded"
                @documentsadded="documentsDocumentsAdded"
                @imagesconverted="documentsImagesConverted"
                ref="documentUploader" />
            </div>
          </div>
        </div>
      </div>

      <div v-show="step === 1300" class="container">
        <div class="row justify-content-center">
          <div class="col-sm-9 col-md-6 mt-3">
            <button
              type="button"
              class="btn btn-outline-primary d-block w-100 mb-3"
              :disabled="true">
              <i class="fa fa-plus"></i>
              Weiteres Dokument scannen
            </button>
            <button
              type="button"
              class="btn btn-outline-primary d-block w-100"
              @click="gotoStep(1110)">
              <i class="fa fa-plus"></i>
              Weitere Dateien hochladen
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="sticky-bottom bg-body py-2">
      <div class="container">
        <div class="row justify-content-center">
          <div class="col-md-9 col-lg-6 text-center">
            <template v-if="3000 < step && step < 3100">
              <button
                type="button"
                @click="pdfRedactionRedact()"
                class="btn btn-primary d-block w-100"
                :disabled="pdfRedactionProcessing">
                <span
                  class="spinner-border spinner-border-sm"
                  v-show="pdfRedactionProcessing"
                  role="status"
                  aria-hidden="true" />
                Ich bin fertig mit Schwärzen
              </button>
              <div class="mt-2">
                <small> Wichtig: Haben Sie alle Seiten überprüft? </small>
                <div v-if="debug" class="debug">
                  DEBUG: hasRedactions={{ pdfRedactionCurrentHasRedactions }}
                </div>
              </div>
            </template>
            <template v-else-if="step === 4413">
              <button
                type="button"
                @click="approveDocsAndSubmit()"
                class="btn btn-primary d-block w-100"
                :disabled="isSubmitting || !validity.form">
                <span
                  class="spinner-border spinner-border-sm"
                  v-show="isSubmitting"
                  role="status"
                  aria-hidden="true" />
                Bestätigen
              </button>
              <div class="mt-2" v-if="!validity.form">
                <small>
                  Das Formular enthält noch Fehler.
                  <!-- TODO: we could go through all elements, validate, and report here -->
                </small>
              </div>
              <div class="mt-2" v-if="!object_public">
                <small>
                  Ihre Anfrage ist derzeit nicht öffentlich. Diese Dokumente
                  werden deshalb nicht öffentlich verfügbar.
                </small>
              </div>
              <!-- 
                TODO
                There is a feature missing here:
                if public and is_staff, offer checkboxes to opt-out of auto-approving the uploaded attachments.
                Approval is currently set by the redact_attachment_task.
                Changing this default would necessitate deeper changes to how/when/where approval is set.
                <template v-if="object_public && user_is_staff">
                  Um Dokumente vorerst nicht zu veröffentlichen, die Häkchen entfernen.
                </template>
              -->
            </template>
            <template v-else-if="step === 4570">
              <button
                type="button"
                @click="submit"
                class="btn btn-primary d-block w-100">
                Anfrage ansehen
              </button>
            </template>
            <template v-else-if="step === 1100">
              <!-- should be blank -->
              <button
                v-if="debug"
                type="button"
                @click="gotoStep()"
                class="action btn btn-outline-primary btn-sm mt-1">
                DEBUG skip
              </button>
            </template>
            <template v-else-if="step === 1110">
              <!-- this could be completely hidden -->
              <button
                type="button"
                :disabled="true"
                class="btn btn-primary d-block w-100">
                weiter
              </button>
              <button
                v-if="debug"
                type="button"
                @click="gotoStep()"
                class="action btn btn-outline-primary btn-sm mt-1">
                DEBUG skip
              </button>
            </template>
            <template v-else-if="step === 1201">
              <button
                type="button"
                @click="gotoStep()"
                class="btn btn-primary d-block w-100">
                Fertig mit Sortieren
              </button>
            </template>
            <template v-else-if="step === 1202">
              <button
                v-if="documentUploader.$refs.imageDocument.length > 0"
                type="button"
                @click="documentsConvertImages"
                class="btn btn-primary d-block w-100"
                :disabled="documentsImagesConverting">
                <span
                  class="spinner-border spinner-border-sm"
                  v-if="documentsImagesConverting"
                  role="status"
                  aria-hidden="true" />
                PDF erstellen
              </button>
              <button
                v-else
                type="button"
                @click="gotoStep()"
                class="btn btn-primary d-block w-100">
                weiter
              </button>
            </template>
            <template v-else-if="step === 2384">
              <button
                type="button"
                :disabled="!gotoValid"
                @click="gotoStep()"
                class="btn btn-primary d-block w-100">
                weiter
              </button>
              <button
                v-if="debug"
                type="button"
                @click="debugSkipDate"
                class="btn btn-outline-primary btn-sm mt-1 d-block w-100">
                DEBUG set today
              </button>
            </template>
            <template v-else>
              <button
                type="button"
                @click="gotoStep()"
                :disabled="!gotoValid"
                class="btn btn-primary d-block w-100">
                weiter
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
  </div>
</template>

<style lang="scss" scoped>
@use 'sass:map';
@import 'bootstrap/scss/functions';
@import '../../../styles/variables.scss';

.debug {
  opacity: 0.5 !important;
  color: #888 !important;

  &.btn {
    color: black !important;
  }
}

/* stretch "main" so actions-footer always sticks to the bottom,
 * giving it an app-like feel */

.postupload-main {
  // header
  //   #header nav's padding
  //   #header nav .navlogo svg's height
  //   .breadcrumb's padding
  //   breadcrumb-item's line-height
  // footer (sticky)
  //   py-2
  //   btn's padding
  //   btn's height
  min-height: calc(
    100vh - (2 * 1rem + 2.5rem) - (2 * 0.5rem + 1.5rem * 14 / 16) -
      (2 * 0.5rem + 2 * 0.375rem + 1.5rem)
  );
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

/* make links stand out more in alert boxes */

.alert {
  a {
    text-decoration: underline;
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

/* bootstrap doesn't provide this responsive position class out of the box
 * (it could be compiled in with utils/helpers)
 * used here to un-sticky the stepper in the header */

.position-md-static {
  @media (min-width: map.get($grid-breakpoints, 'md')) {
    position: static;
  }
}
</style>
