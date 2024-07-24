<script setup>
import {
  ref,
  reactive,
  computed,
  defineProps,
  defineEmits,
  nextTick,
  watch
} from 'vue'
import AppShell from './app-shell.vue'
import PublicbodyChooser from '../publicbody/publicbody-chooser'
// TODO linter wrong? the two above are just fine...
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import DocumentUploader from '../docupload/document-uploader.vue'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import PdfRedaction from '../redaction/pdf-redaction.vue'
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
// TODO sync this media query with AppShell's + also with scss here
const isDesktopMediaQueryList = window.matchMedia('(min-width: 1000px)')
updateIsDesktop(isDesktopMediaQueryList)
isDesktopMediaQueryList.addEventListener('change', updateIsDesktop)

const stepHistory = reactive([1100])
const step = computed(() =>
  stepHistory.length ? stepHistory[stepHistory.length - 1] : false
)

const formSent = ref(
  props.form.fields.sent.value?.toString() ||
    props.form.fields.sent.initial?.toString() ||
    '0'
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
const formStatusChoices = computed(() =>
  props.status_form.fields.resolution.choices.filter((choice) => {
    if (formIsSent.value) {
      switch (choice.value) {
        case 'successful':
        case 'partially_successful':
        case 'not_held':
        case 'refused':
          return false
      }
    } else {
      if (choice.value === 'user_withdrew_costs') return false
    }
    return true
  })
)

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

const progress = computed(() => {
  // roughly map to {0, ½, 1}
  return Math.min(Math.floor((step.value - 1000) / 1000), 2) / 2
})

const progressStep = computed(() =>
  // map to {0, 1, 2}
  Math.min(Math.floor((step.value - 1000) / 1000), 2)
)

const gotoStep = (nextStep) => {
  stepHistory.push(nextStep || getNextStep())
}

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
    return validity.date && validity.registered_mail
  }
  if (step.value === 2382) {
    return validity.registered_mail
  }
  if (step.value === 2384) {
    return validity.date
  }
  return true
})

const backStep = () => {
  stepHistory.pop()
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
      if (documentsImageMode.value) return 1201
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
      documentsImagesDocumentFilename.value =
        documentsImagesDocumentFilenameDefault
      break
    case 1300:
      pdfRedactionUploaded()
      break
    case 2382:
      updateValidity('registered_mail')
      break
    case 2384:
      updateValidity('date')
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
  }
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
  registered_mail: false
})

// TODO updateValidity should (maybe) be called on gotoStep(2384), too
const updateValidity = (key) => {
  const el =
    key === 'form'
      ? document.forms.postupload
      : document.forms.postupload.elements[key]
  // just assume true if browser doesn't support checkValidity
  validity[key] = 'checkValidity' in el ? el.checkValidity() : true
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
  updateValidity('date')
  gotoStep()
}

defineEmits(['showhelp'])
</script>

<template>
  <app-shell
    :progress="progress"
    :step="progressStep"
    :steps="['Hochladen', 'Infos eingeben', 'Schwärzen']">
    <template #mobile-header-title1>
      <template v-if="false"> Frag den Staat </template>
      <template v-else-if="step < 4000">
        {{ i18n.step }} {{ Math.floor(step / 1000)
        }}<b class="header-title1-bold">/3</b>
      </template>
      <template v-else-if="step >= 4000">
        <small>Fertig</small>
      </template>
      <span v-if="debug" class="debug">({{ step }})</span>
      <span v-if="debug" class="debug">
        <!-- eslint-disable-next-line vue/no-mutating-props -->
        <button type="button" @click="user_is_staff = !user_is_staff">
          {{ user_is_staff ? '☑' : '☐' }} staff
        </button>
      </span>
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
    </template>
    <template #mobile-header-title2>
      {{ mobileHeaderTitle2 }}
    </template>
    <template #nav>
      <!-- TODO button does not support going back throug documentsPdfRedactionIndex -->
      <div v-if="step === 1100" class="my-3">
        <a href="../.." class="btnlike">← <u>Abbrechen</u></a>
      </div>
      <div v-else-if="step !== 4570" class="my-3">
        <a @click="backStep" class="btnlike">← <u>Zurück</u></a>
      </div>
      <button
        v-if="debug"
        class="btn btn-secondary btn-sm debug"
        type="submit"
        style="font-size: 50%; margin-left: 1em">
        submit/save
      </button>
      <button
        v-if="debug"
        class="btn btn-secondary btn-sm debug"
        type="button"
        @click="submitFetch"
        style="font-size: 50%; margin-left: 1em">
        submit/fetch
      </button>
    </template>
    <template #main="{ onShowhelp }">
      <details v-if="debug && form.nonFieldErrors.length">
        <summary class="debug">DEBUG form.nonFieldErrors</summary>
        <pre>{{ form.nonFieldErrors }}</pre>
      </details>
      <details v-if="debug && Object.keys(form.errors).length">
        <summary class="debug">DEBUG form.errors</summary>
        <pre>{{ form.errors }}</pre>
      </details>

      <div v-show="step === 1100">
        <button disabled class="btn btn-outline-primary d-block w-100">
          <i class="fa fa-camera"></i>
          Dokumente scannen
        </button>
        <p class="mt-1">
          Handykamera verwenden, um automatisch ein PDF zu erstellen
        </p>
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
        <aside>
          <h4><i class="fa fa-lightbulb-o fa-lg"></i> TIPP</h4>
          <p>
            Sie brauchen den Brief vorher <strong>nicht</strong> zu schwärzen.
            Das erledigen Sie später mit unserem Online-Tool.
          </p>
          <p>Wir führen Sie Schritt für Schritt durch den Prozess.</p>
        </aside>
      </div>

      <div v-show="step === 1110">
        <!-- document-uploader see below -->
      </div>

      <div v-show="step === 1201">
        <label class="fw-bold form-label">
          Ziehen Sie die Seiten in die richtige Reihenfolge
        </label>
      </div>

      <div v-show="step === 1202">
        <div>
          <div class="text-center my-3">
            <i class="fa fa-file-image-o fa-4x"></i>
            <i class="fa fa-arrow-right fa-2x"></i>
            <i class="fa fa-file-pdf-o fa-4x"></i>
          </div>
        </div>
        <div class="fw-bold form-label">
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

      <!-- there is another for this step, further down below document-uploader -->
      <div v-show="step === 1300">
        <div class="fw-bold">Bisher vorhandene Dokumente</div>
      </div>

      <div v-show="step === 2376">
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
            :value="choice.value"
            :data-x-checked="
              form.fields.sent.value === choice.value ||
              form.fields.sent.initial === choiceIndex
            " />
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

      <div v-show="step === 2380">
        <!-- also 2428 -->
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

      <div
        v-show="
          step === 2381 ||
          (isDesktop && step === 2380 && !formPublicbodyIsDefault)
        "
        class="step--desktopindent">
        <!-- also 2429 -->
        <label class="fw-bold form-label" for="id_subject">
          <template v-if="formSent === '1'">
            An welche Behörde haben Sie den Brief gesendet?
          </template>
          <template v-else> Von welcher Behörde stammt der Brief? </template>
        </label>
        <publicbody-chooser
          v-if="!formPublicbodyIsDefault"
          :search-collapsed="true"
          scope="foo_publicbody"
          name="publicbody"
          :config="config"
          :form="form"
          :value="formPublicbodyId"
          list-view="resultList"
          :class="{ 'is-invalid': form.errors.publicbody }" />
      </div>

      <div v-show="step === 2384">
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

      <div
        v-show="
          step === 2382 ||
          (isDesktop && step === 2384 && values.is_registered_mail)
        "
        class="step--desktopindent">
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
          id="id_registered_mail"
          name="registered_mail"
          :required="values.is_registered_mail"
          @input="updateValidity('registered_mail')"
          v-model="values.registered_mail" />
      </div>

      <div v-show="step === 2437">
        <!-- also 2386,2435,2440 -->
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
            Ihre Anfrage war bereits abgeschlossen. Ist dies nach Versenden des
            Briefes noch immer der Fall?
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

      <div
        v-show="
          step === 2438 || (isDesktop && step === 2437 && formStatusIsResolved)
        "
        class="step--desktopindent">
        <!-- also 2387,2436,2439 -->
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
            required=""
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

      <div v-show="step === 2388">
        <div class="step-questioncounter">Frage 5 von 5</div>
        <label class="fw-bold col-form-label" for="">
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
          <label class="form-check-label" :for="'id_nowcost_' + choiceIndex">{{
            choice.label
          }}</label>
        </div>
      </div>

      <div v-show="step === 2390">
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
          <label class="form-check-label" :for="'id_nowcost_' + choiceIndex">{{
            choice.label
          }}</label>
        </div>
      </div>

      <div v-show="step === 3402">
        <label class="fw-bold col-form-label">
          Welche dieser Dokumente möchen Sie schwärzen?
        </label>
        <!-- TODO: if we expect users to go back a lot, the document-uploader list
          shown here should exclude/disable "has schwärzung" docs -->
        <p>
          Ein Dokument sollte geschwärzt werden, wenn es personenbezogene
          Informationen über Sie selbst oder Behördenmitarbeiter:innen enthält.
        </p>
        <div class="text-end">
          <button
            type="button"
            class="btn-linklike mx-2"
            @click="documentUploaderSelectAll(true)">
            Alle auswählen
          </button>
          <button
            type="button"
            class="btn-linklike mx-2"
            @click="documentUploaderSelectAll(false)">
            Keine auswählen
          </button>
        </div>
      </div>

      <div v-show="3000 < step && step < 3100">
        <label class="fw-bold col-form-label">
          Dokument schwärzen ({{ documentsPdfRedactionIndex + 1 }} von
          {{ documentsSelectedPdfRedaction.length }})
        </label>
        <aside>
          Das sollten Sie schwärzen:
          <ul>
            <li>Ihren Namen und Ihre Adresse</li>
            <li>Namen von Behördenmitarbeiter:innen</li>
            <li>Unterschriften</li>
            <li>E-Mail-Adressen, die auf ‘@fragdenstaat.de’ enden</li>
          </ul>
        </aside>
        <div class="mt-2 mb-3">
          <button
            type="button"
            class="btn-linklike"
            @click="onShowhelp(config.urls.helpPostuploadRedaction)">
            Ich habe technische Probleme / benötige Hilfe
          </button>
        </div>
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
          ref="pdfRedaction" />
      </div>

      <div v-show="step === 4413">
        <label class="fw-bold col-form-label">
          Diese Dokumente werden der Anfrage hinzugefügt:
        </label>
      </div>

      <div
        v-show="
          step === 2565 ||
          (isDesktop && (step === 2388 || step === 2390) && formDoUpdateCost)
        "
        class="step--desktopindent">
        <label class="fw-bold col-form-label" for="id_costs">
          <!--{{ status_form.fields.costs.label }}-->
          Welchen Betrag hat die Behörde verlangt?
        </label>
        <div class="col-md-8">
          <div class="input-group" style="width: 10rem">
            <!-- type=number does not support pattern -->
            <!-- TODO: client-side validation like with type=date -->
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

      <div v-show="step === 4570">
        <div class="text-center my-3">
          <i class="fa fa-check-square fa-4x"></i>
        </div>
        <label class="fw-bold col-form-label">
          Dokumente erfolgreich hinzugefügt
        </label>
        <div>
          Danke, dass Sie Ihre Anfrage auf den neuesten Stand gebracht haben!
        </div>
      </div>

      <!-- not in v-show="step ..." -->
      <div v-show="uiDocuments">
        <div
          v-if="step === 4413 && !user_is_staff"
          class="d-flex justify-content-end">
          <button
            type="button"
            class="btn-linklike"
            @click="documentsBasicOperations = !documentsBasicOperations">
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
          :images-document-filename="documentsImagesDocumentFilenameNormalized"
          :file-basic-operations="step === 1300 || documentsBasicOperations"
          :hide-advanced-operations="!(debug && user_is_staff)"
          :highlight-redactions="uiDocumentsHighlightRedactions"
          @selectionupdated="documentsSelectedPdfRedaction = $event"
          @imagesadded="documentsImagesAdded"
          @documentsadded="documentsDocumentsAdded"
          @imagesconverted="documentsImagesConverted"
          ref="documentUploader" />
      </div>

      <div v-show="step === 1300">
        <div class="mb-2 mt-5 mx-auto" style="max-width: 20em">
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100"
            :disabled="true">
            <i class="fa fa-plus"></i>
            Weiteres Dokument scannen
          </button>
        </div>
        <div class="my-2 mx-auto" style="max-width: 20em">
          <button
            type="button"
            class="btn btn-outline-primary d-block w-100"
            @click="gotoStep(1110)">
            <i class="fa fa-plus"></i>
            Weitere Dateien hochladen
          </button>
        </div>
      </div>
    </template>

    <template #actions>
      <!--<template v-if="step === 3001">-->
      <template v-if="3000 < step && step < 3100">
        <button
          type="button"
          @click="pdfRedactionRedact()"
          class="action btn btn-primary"
          :disabled="pdfRedactionProcessing">
          <span
            class="spinner-border spinner-border-sm"
            v-if="pdfRedactionProcessing"
            role="status"
            aria-hidden="true" />
          Ich bin fertig mit Schwärzen
        </button>
        <div class="action-info">
          Wichtig: Haben Sie alle Seiten überprüft?
          <div v-if="debug" class="debug">
            DEBUG: hasRedactions={{ pdfRedactionCurrentHasRedactions }}
          </div>
        </div>
      </template>
      <template v-else-if="step === 4413">
        <button
          type="button"
          @click="approveDocsAndSubmit()"
          class="action btn btn-primary"
          :disabled="isSubmitting || !validity.form">
          <span
            class="spinner-border spinner-border-sm"
            v-show="isSubmitting"
            role="status"
            aria-hidden="true" />
          Bestätigen
        </button>
        <div class="action-info">
          <template v-if="!validity.form">
            Das Formular enthält noch Fehler.
            <!-- TODO: we could go through all elements, validate, and report here -->
          </template>
          <template v-if="!object_public">
            Ihre Anfrage ist derzeit nicht öffentlich. Diese Dokumente werden
            deshalb nicht öffentlich verfügbar.
          </template>
          <!--<template v-if="object_public && user_is_staff">
            Um Dokumente vorerst nicht zu veröffentlichen, die Häkchen
            entfernen. TODO
          </template>-->
        </div>
      </template>
      <template v-else-if="step === 4570">
        <button type="button" @click="submit" class="action btn btn-primary">
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
        <button type="button" :disabled="true" class="action btn btn-primary">
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
          class="action btn btn-primary">
          Fertig mit Sortieren
        </button>
      </template>
      <template v-else-if="step === 1202">
        <button
          v-if="documentUploader.$refs.imageDocument.length > 0"
          type="button"
          @click="documentsConvertImages"
          class="action btn btn-primary"
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
          class="action btn btn-primary">
          weiter
          <span class="debug" v-if="debug">DEBUG: skip pdf</span>
        </button>
      </template>
      <template v-else-if="step === 2384">
        <button
          type="button"
          :disabled="!gotoValid"
          @click="gotoStep()"
          class="action btn btn-primary">
          weiter
        </button>
        <button
          v-if="debug"
          type="button"
          @click="debugSkipDate"
          class="action btn btn-outline-primary btn-sm mt-1">
          DEBUG set today
        </button>
      </template>
      <template v-else>
        <button
          type="button"
          @click="gotoStep()"
          :disabled="!gotoValid"
          class="action btn btn-primary">
          weiter
        </button>
      </template>
    </template>
  </app-shell>
</template>

<style lang="scss" scoped>
$breakpoint: 1000px;

.debug {
  opacity: 0.5 !important;
  color: #888 !important;

  &.btn {
    color: black !important;
  }
}

.header-title1-bold {
  color: black;
}

a.btnlike {
  color: var(--bs-link-color);
  cursor: pointer;

  &:hover {
    text-decoration: none;
  }
}

.btn-linklike {
  border: none;
  padding: 0;
  color: var(--bs-link-color);
  text-decoration: underline;
  background: transparent;
}

@media (min-width: $breakpoint) {
  .step--desktopindent {
    padding: 2em 0 0 4em;
  }
}

.step-questioncounter {
  display: none;

  @media (min-width: $breakpoint) {
    display: block;
  }
}

.form-check {
  background-color: #eee;
  // padding: 1em 1em 1em 2.25em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

.form-check label {
  padding: 1em;
  display: block;
}

.form-check-input {
  margin-top: 1.25em;
  margin-left: -0.66em;
  border-color: black;
  border-width: 2px;

  &:checked {
    background-color: black;
  }
}

.action-info {
  margin: 0.5rem auto 0 auto;
  font-size: 66%;
  max-width: 30em;
  text-align: center;
}

.action.btn {
  display: block;
  width: 100%;
  max-width: 30em;
  margin: 0 auto;
}

/*
input[type='date']:valid {
  border-color: green;
}

input[type='date']:invalid {
  border-color: red;
}
*/

aside {
  padding: 1em;
  background-color: #fbde85;
}

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
    color: red;
    text-decoration: underline;
    color: var(--bs-link-color);
    /* padding-left matches bootstrap's form-group>input for indent */
    padding: 0.25rem 0.25rem 0.25rem 0.75rem;
  }
}
</style>
