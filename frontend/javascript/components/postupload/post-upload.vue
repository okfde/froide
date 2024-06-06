<script setup>
import { ref, reactive, computed, defineProps } from 'vue'
import AppShell from './app-shell.vue'
import PublicbodyChooser from '../publicbody/publicbody-chooser'
import DocumentUploader from '../docupload/document-uploader.vue'
import PdfRedaction from '../redaction/pdf-redaction.vue'

const props = defineProps({
  config: Object,
  form: Object,
  message: Object,
  status_form: Object,
  object_public_body_id: String,
  object_public: Boolean,
  date_min: String,
  date_max: String,
  user_is_staff: Boolean
})

const stepHistory = reactive([1100])
const step = computed(() =>
  stepHistory.length ? stepHistory[stepHistory.length - 1] : false
)

const formSent = ref(
  props.form.fields.sent.value || props.form.fields.sent.initial
)
const formIsSent = computed(() => formSent.value === '1')

const formPublicbodyIsDefault = ref(true)

const formStatus = ref(
  props.status_form.fields.status.value ||
    props.status_form.fields.status.initial
)
const formStatusWasResolved = formStatus.value === 'resolved'

const formCost = props.status_form.fields.costs.initial?.intValue || 0
const formHasHadCost = formCost > 0

const formDoUpdateCost = ref(false)

const formPublicbodyId =
  props.form.fields.publicbody.value ||
  props.form.fields.publicbody?.initial?.id?.toString() ||
  props.object_public_body_id

const formPublicbodyLabel =
  props.form.fields.publicbody.choices.find(
    (choice) => choice.value === formPublicbodyId
  )?.label || 'Error'

const documentsSelectedPdfRedaction = ref([])
const documentsPdfRedactionIndex = ref(0)
const currentPdfRedactionDoc = computed(
  () => documentsSelectedPdfRedaction.value[documentsPdfRedactionIndex.value]
)

const mobileHeaderTitle2 = computed(() => {
  if (2000 <= step.value && step.value < 3000) {
    return 'Infos eingeben'
  }
  if (3000 <= step.value && step.value < 4000) {
    return 'Schwärzen'
  }
  if (step.value >= 4000) {
    return 'Vorschau'
  }
  switch (step.value) {
    case 1100:
      return 'Brief hinzufügen'
    case 1110:
      return 'Brief hochladen oder scannen'
    default:
      return '(Untertitel)'
  }
})

const progress = computed(() => {
  // roughly map to {⅓ ,⅔,1}
  return Math.min(Math.floor(step.value / 1000), 3) / 3
})

const gotoStep = () => {
  stepHistory.push(getNextStep())
}

const gotoValid = computed(() => {
  switch (step.value) {
    case 2382:
      return validity.yellowDate
    case 2384:
      return validity.date
  }
  return true
})

const backStep = () => {
  stepHistory.pop()
}

const submit = () => {
  document.forms.postupload.submit()
}

// TODO WIP numbers from Figma frames
const getNextStep = () => {
  switch (step.value) {
    case 1100:
      return 1110
    case 1110:
      return 2376
    case 2376:
      return 2380
    case 2380:
      return formPublicbodyIsDefault.value ? 2384 : 2381
    case 2381:
      return 2384
    case 2384:
      return values.isYellow ? 2382 : 2437
    case 2382:
      return 2437
    case 2437:
      if (formStatus.value === 'resolved') return 2438
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
      return 3001
    case 3001:
      if (
        documentsPdfRedactionIndex.value <
        documentsSelectedPdfRedaction.value.length - 1
      ) {
        documentsPdfRedactionIndex.value++
        return 3001
      }
      return 4413
    case 4413:
      return 4570
    case 4570:
      return 4570
  }
}

const stepUiConf = {
  1110: {
    documents: true,
    documentsUpload: true,
    documentsHideSelection: true
  },
  3402: {
    documents: true
  },
  4413: {
    documents: true,
    documentsHideSelection: !(props.object_public && props.user_is_staff)
  }
}

const uiDocuments = computed(() => stepUiConf[step.value]?.documents || false)
const uiDocumentsUpload = computed(
  () => stepUiConf[step.value]?.documentsUpload || false
)
const uiDocumentsHideSelection = computed(
  () => stepUiConf[step.value]?.documentsHideSelection || false
)

const pdfRedactionUploaded = () => {
  gotoStep()
}

const validity = reactive({
  date: false,
  yellowDate: false
})

const updateValidity = (key, evt) => {
  console.log(evt, evt.currentTarget.checkValidity())
  // just assume true if browser doesn't support checkValidity
  validity[key] =
    'checkValidity' in evt.currentTarget
      ? evt.currentTarget.checkValidity()
      : true
}

const values = reactive({
  // FIXME date doesn't populate from a saved form?
  date: props.form.fields.date.value,
  costs:
    props.status_form.fields.costs.value?.strValue ||
    props.status_form.fields.costs.initial.strValue,
  isYellow: false
})
</script>

<template>
  <app-shell :progress="progress">
    <template #mobile-header-title1>
      <template v-if="false"> Frag den Staat </template>
      <template v-else-if="step < 4000">
        Schritt {{ Math.floor(step / 1000)
        }}<b class="header-title1-bold">/3</b>
      </template>
      <template v-else-if="step >= 4000">
        <small>Fertig</small>
      </template>
      <span class="debug">({{ step }})</span>
      <!--<span class="debug">{{ stepHistory.join(',') }}</span>-->
      <!--<span class="debug">p{{ progress }}</span>-->
      <!--<small>{{ { uiDocuments, uiDocumentsUpload } }}</small>-->
      <!--<span class="debug">{{ values.isYellow }}</span>-->
      <!--<span class="debug">{{ gotoValid }}</span>-->
      <!--<span class="debug">
        {{ { pbv: props.form.fields.publicbody.value, pbii:  props.form.fields.publicbody?.initial?.id, opbi: object_public_body_id } }}
      </span>-->
      <!--<span class="debug">formStatus={{formStatus}}</span>-->
      <!--<span class="debug">{{documentsSelectedPdfRedaction}}</span>-->
      <!--<span class="debug">documentsSelectedPdfRedaction={{ documentsSelectedPdfRedaction.map(d => d.id).join(',') }}</span>-->
    </template>
    <template #mobile-header-title2>
      {{ mobileHeaderTitle2 }}
    </template>
    <template #nav>
      <!-- TODO button does not support going back throug documentsPdfRedactionIndex -->
      <a v-if="step === 1100" href="../.." class="btnlike"
        >← <u>Abbrechen</u></a
      >
      <a v-else @click="backStep" class="btnlike">← <u>Zurück</u></a>
      <button
        class="btn btn-secondary btn-sm debug"
        type="submit"
        style="font-size: 50%; margin-left: 1em">
        submit/save
      </button>
    </template>
    <template #main>
      <pre style="border: 2px solid mauve" v-if="form.nonFieldErrors.length">
        form.nonFieldErrors =
        {{ form.nonFieldErrors }}
      </pre>
      <pre
        style="border: 2px solid mauve"
        v-if="Object.keys(form.errors).length">
        form.errors =
        {{ form.errors }}
      </pre>
      <div v-show="step === 1100">
        <button disabled class="btn btn-primary">Dokumente scannen</button>
        <p>Handykamera verwenden...</p>
        <button type="button" @click="gotoStep" class="btn btn-primary">
          Dateien hochladen
        </button>
        <p>Wenn Sie den Brief...</p>
        <aside>
          <b>TIPP</b>
          <p>Sie brauchen den Brief...</p>
        </aside>
      </div>

      <div v-show="step === 1110">
        <!-- document-uploader see below -->
      </div>

      <div v-show="step === 2376">
        <label class="fw-bold form-label field-required">
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

      <div v-show="step === 2381">
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
        <label class="fw-bold form-label field-required" for="id_date">
          Wann wurde der Brief versendet?
          <!--{{ form.fields.date.label }}-->
        </label>
        <input
          id="id_date"
          class="form-control"
          type="date"
          name="date"
          v-model="values.date"
          :class="{ 'is-invalid': form.errors.date }"
          :required="step === 2384"
          :min="props.date_min"
          :max="props.date_max"
          @input="updateValidity('date', $event)"
          :x-placeholder="form.fields.date.placeholder" />
        <!--<div class="form-text">
          {{ form.fields.date.help_text }}
        </div>-->
        <div class="form-check">
          <input
            class="form-check-input"
            type="checkbox"
            v-model="values.isYellow"
            id="id_yellow" />
          <label class="form-check-label" for="id_yellow">
            Es handelt sich um einen gelben Brief ⓘ TODO
          </label>
        </div>
        <div class="invalid-feedback" v-if="form.errors.date">
          <p class="text-danger">
            {{ form.errors.date.map((_) => _.message).join(' ') }}
          </p>
        </div>
      </div>

      <div v-show="step === 2382">
        <label class="fw-bold form-label field-required" for="id_yellowdate">
          Gelber Brief: Welches Zustelldatum wurde auf dem Briefumschlag
          eingetragen?
        </label>
        <!-- TODO these are the same as the other date-->
        <input
          type="date"
          class="form-control"
          name="yellow_date"
          :min="props.date_min"
          :max="props.date_max"
          :required="step === 2382"
          @input="updateValidity('yellowDate', $event)"
          v-model="values.yellowDate" />
      </div>

      <div v-show="step === 2437">
        <!-- also 2386,2435,2440 -->
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

      <div v-show="step === 2438">
        <!-- also 2387,2436,2439 -->
        <label class="fw-bold col-md-4 col-form-label" for="id_resolution">
          <!-- {{ status_form.fields.resolution.label }} -->
          Wie würde Sie das Ergebnis beschreiben?
        </label>
        <div
          class="form-check"
          v-for="(choice, choiceIndex) in status_form.fields.resolution.choices"
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
        <label class="fw-bold col-md-4 col-form-label" for="">
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
        <label class="fw-bold col-md-4 col-form-label" for="id_nowcost">
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
        <label class="fw-bold col-md-4 col-form-label">
          Welche Dieser Dokumente möchen Sie schwärzen?
        </label>
        <div>
          <a>Alle auswählen TODO</a>
          <a>Keine auswählen</a>
        </div>
      </div>

      <div v-show="step === 3001">
        <label class="fw-bold col-md-4 col-form-label">
          Dokument schwärzen ({{ documentsPdfRedactionIndex + 1 }} von
          {{ documentsSelectedPdfRedaction.length }})
        </label>
        <aside>
          Das sollten Sie schwärzen:
          <ul>
            <li>Ihre Namen…</li>
          </ul>
        </aside>
        <div>
          <a><u>Ich habe technische Probleme TODO</u></a>
        </div>
        <pre>documentsPdfRedactionIndex = {{ documentsPdfRedactionIndex }}</pre>
        <pre>currentPdfRedactionDoc = {{ currentPdfRedactionDoc }}</pre>
        <!-- optionally iframe? -->
        <pdf-redaction
          v-if="step === 3001 && currentPdfRedactionDoc"
          :key="currentPdfRedactionDoc.id"
          :pdf-path="currentPdfRedactionDoc.attachment.file_url"
          :attachment-url="currentPdfRedactionDoc.attachment.anchor_url"
          :post-url="
            config.url.redactAttachment.replace(
              '/0/',
              '/' + currentPdfRedactionDoc.id + '/'
            )
          "
          :no-redirect="true"
          :redact-regex="['teststraße\ 1']"
          :can-publish="true"
          :config="config"
          @uploaded="pdfRedactionUploaded" />
      </div>

      <div v-show="step === 4413">
        <label class="fw-bold col-md-4 col-form-label">
          Diese Dokumente werden der Anfrage hinzugefügt:
        </label>
        <div><a>Bearbeiten TODO</a></div>
      </div>

      <div v-show="step === 2565">
        <label class="fw-bold col-md-4 col-form-label" for="id_costs">
          <!--{{ status_form.fields.costs.label }}-->
          Welchen Betrag hat die Behörde verlangt?
        </label>
        <div class="col-md-8">
          <div class="input-group" style="width: 10rem">
            <input
              type="number"
              name="costs"
              id="id_costs"
              class="form-control col-3"
              inputmode="decimal"
              pattern="[0-9]+([\.,][0-9]+)?"
              style="appearance: textfield; text-align: right"
              min="0"
              max="1000000000"
              step="0.01"
              x-value="
                status_form.fields.costs.value?.strValue ||
                status_form.fields.costs.initial.strValue
              "
              v-model="values.costs"
              :class="{ 'is-invalid': status_form.errors.costs }" />
            <span class="input-group-text">Euro</span>
          </div>
          <!--<div class="form-text">{{ status_form.fields.costs.help_text }}</div>-->
        </div>
      </div>

      <div v-show="step === 4570">
        <label class="fw-bold col-md-4 col-form-label">
          Dokumente erfolgreich hinzugefügt
        </label>
        <div>
          Danke, dass Sie Ihre Anfrage auf den neuesten Stand gebracht haben!
        </div>
      </div>

      <!-- not in v-show="step ..." -->
      <div v-show="uiDocuments">
        <document-uploader
          :config="config"
          :message="message"
          :show-upload="uiDocumentsUpload"
          :hide-selection="uiDocumentsHideSelection"
          @selectionupdated="documentsSelectedPdfRedaction = $event" />
      </div>
    </template>

    <template #actions>
      <template v-if="step === 3001">
        <button type="button" @click="gotoStep" class="action btn btn-primary">
          Ich bin fertig mit Schwärzen
        </button>
        <div class="action-info">Wichtig: Haben Sie alle Seiten überprüft?</div>
      </template>
      <template v-else-if="step === 4413">
        <button type="button" @click="gotoStep" class="action btn btn-primary">
          Bestätigen
        </button>
        <div class="action-info">
          <template v-if="!object_public">
            Ihre Anfrage ist derzeit nicht öffentlich. Diese Dokumente werden
            deshalb nicht öffentlich verfügbar.
          </template>
          <template v-if="object_public && user_is_staff">
            Um Dokumente vorerst nicht zu veröffentlichen, die Häkchen
            entfernen. TODO
          </template>
        </div>
      </template>
      <template v-else-if="step === 4570">
        <button type="button" @click="submit" class="action btn btn-primary">
          Anfrage ansehen
        </button>
      </template>
      <template v-else>
        <button
          type="button"
          @click="gotoStep"
          :disabled="!gotoValid"
          class="action btn btn-primary">
          weiter
        </button>
      </template>
    </template>
  </app-shell>
</template>

<style lang="scss" scoped>
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

input[type='date']:valid {
  border-color: green;
}

input[type='date']:invalid {
  border-color: red;
}
</style>
