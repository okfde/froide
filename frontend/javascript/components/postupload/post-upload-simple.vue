<!-- this file is a proof-of-concept/practice implementation of the vanilla Django form as Vue -->
<template>
  <div>
    <!--<pre>
    form.errors:
      {{ form.errors }}
    status_form.errors:
      {{ status_form.errors }}
    </pre>-->
    <fieldset>
      <div class="alert alert-danger" v-if="form.errors.__all__">
        <div v-for="error in form.errors.__all__" :key="error.message">
          {{ error.message }}
        </div>
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label field-required">
          {{ form.fields.sent.label }}
        </label>
        <div
          class="form-check"
          v-for="(choice, choiceIndex) in form.fields.sent.choices"
          :key="choice.value"
          :class="{ 'is-invalid': choice.errors }">
          <input
            type="radio"
            name="sent"
            required=""
            class="form-check-input"
            :id="'id_sent_' + choiceIndex"
            :value="choice.value"
            :checked="
              form.fields.sent.value === choice.value ||
              form.fields.sent.initial === choiceIndex
            " />
          <label class="form-check-label" :for="'id_sent_' + choiceIndex">{{
            choice.label
          }}</label>
        </div>
        <div class="invalid-feedback" v-if="form.errors.sent">
          <p class="text-danger">
            {{ form.errors.sent.map((_) => _.message).join(' ') }}
          </p>
        </div>
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label field-required">
          {{ form.fields.sent.label }}
        </label>
        <!-- to populate its "selected publicbody" this component looks for
          this.form.fields[this.name]
        -->
        <publicbody-chooser
          :search-collapsed="true"
          scope="foo_publicbody"
          name="publicbody"
          :config="config"
          :form="form"
          :value="object_public_body_id"
          list-view="resultList"
          :class="{ 'is-invalid': form.errors.publicbody }" />
        <div class="invalid-feedback" v-if="form.errors.publicbody">
          <p class="text-danger">
            {{ form.errors.publicbody.map((_) => _.message).join(' ') }}
          </p>
        </div>
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label field-required" for="id_date">
          {{ form.fields.date.label }}
        </label>
        <input
          id="id_date"
          class="form-control"
          type="text"
          name="date"
          required=""
          :value="form.fields.date.value"
          :class="{ 'is-invalid': form.errors.date }"
          :placeholder="form.fields.date.placeholder" />
        <div class="form-text">
          {{ form.fields.date.help_text }}
        </div>
        <div class="invalid-feedback" v-if="form.errors.date">
          <p class="text-danger">
            {{ form.errors.date.map((_) => _.message).join(' ') }}
          </p>
        </div>
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label" for="id_subject">
          {{ form.fields.subject.label }}
        </label>
        <input
          type="text"
          name="subject"
          class="form-control"
          maxlength="230"
          id="id_subject"
          :placeholder="form.fields.subject.placeholder"
          :value="form.fields.subject.value" />
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label field-required" for="id_date">
          {{ form.fields.uploads.label }}
        </label>
        <file-uploader
          :config="config"
          name="uploads"
          :allowed-file-types="['.pdf', '.jpg', '.jpeg', '.png', '.gif']"
          :auto-proceed="true" />
        <div class="form-text">
          {{ form.fields.uploads.help_text }}
        </div>
      </div>
      <div class="mb-3">
        <label class="fw-bold form-label" for="id_text">
          {{ form.fields.text.label }}
        </label>
        <textarea
          name="text"
          cols="40"
          rows="4"
          class="form-control"
          id="id_text"
          :value="form.fields.text.value" />
        <div class="form-text">
          {{ form.fields.text.help_text }}
        </div>
      </div>
    </fieldset>
    <fieldset>
      <legend>
        <django-slot name="status-legend" />
      </legend>
      <fieldset class="row mb-3">
        <legend class="fw-bold col-form-label col-md-4 field-required">
          {{ status_form.fields.status.label }}
        </legend>
        <div class="col-md-8">
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
              :value="choice.value"
              :checked="
                status_form.fields.status.value === choice.value ||
                status_form.fields.status.initial === choice.value
              " />
            <label class="form-check-label" :for="'id_status_' + choiceIndex">{{
              choice.label
            }}</label>
          </div>
        </div>
      </fieldset>
      <div class="mb-3 row">
        <label class="fw-bold col-md-4 col-form-label" for="id_resolution">{{
          status_form.fields.resolution.label
        }}</label>
        <div class="col-md-8">
          <select
            name="resolution"
            class="form-select"
            id="id_resolution"
            ref="statusResolution"
            @input="updateRefusalReasonVisibility"
            :class="{ 'is-invalid': status_form.errors.refusal_reason }">
            <option
              v-for="choice in status_form.fields.resolution.choices"
              :key="choice.value"
              :value="choice.value"
              :selected="
                status_form.fields.resolution.value === choice.value ||
                status_form.fields.resolution.initial === choice.value
              ">
              {{ choice.label }}
            </option>
          </select>
          <div class="form-text">
            {{ status_form.fields.resolution.help_text }}
          </div>
        </div>
      </div>
      <div class="mb-3 row" v-if="isRefusalReasonVisible">
        <label
          class="fw-bold col-md-4 col-form-label"
          for="id_refusal_reason"
          >{{ status_form.fields.refusal_reason.label }}</label
        >
        <div class="col-md-8">
          <select
            name="refusal_reason"
            class="form-select"
            id="id_refusal_reason"
            :class="{ 'is-invalid': status_form.errors.refusal_reason }">
            <option
              v-for="choice in status_form.fields.refusal_reason.choices"
              :key="choice.value"
              :value="choice.value"
              :selected="
                status_form.fields.refusal_reason.value === choice.value ||
                status_form.fields.refusal_reason.initial === choice.value
              ">
              {{ choice.label }}
            </option>
          </select>
          <div class="form-text">
            {{ status_form.fields.refusal_reason.help_text }}
          </div>
        </div>
      </div>
      <div class="mb-3 row">
        <label class="fw-bold col-md-4 col-form-label" for="id_costs">{{
          status_form.fields.costs.label
        }}</label>
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
              :value="
                status_form.fields.costs.value?.strValue ||
                status_form.fields.costs.initial.strValue
              "
              :class="{ 'is-invalid': status_form.errors.costs }" />
            <span class="input-group-text">Euro</span>
          </div>
          <div class="form-text">{{ status_form.fields.costs.help_text }}</div>
        </div>
      </div>
    </fieldset>
    <p class="text-end">
      <button type="submit" class="btn btn-primary">
        <django-slot name="submit-text" />
      </button>
    </p>
  </div>
</template>

<script>
import DjangoSlot from '../../lib/django-slot.vue'
import FileUploader from '../upload/file-uploader.vue'
import PublicbodyChooser from '../publicbody/publicbody-chooser'

export default {
  name: 'PostUpload',
  data: function () {
    return {
      isRefusalReasonVisible: false
    }
  },
  components: {
    DjangoSlot,
    FileUploader,
    PublicbodyChooser
  },
  props: {
    config: {
      type: Object,
      required: true
    },
    object_public_body_id: {},
    form: {
      type: Object
    },
    status_form: {
      type: Object
    }
  },
  computed: {
    errors() {
      return this.form.errors
    }
  },
  methods: {
    updateRefusalReasonVisibility() {
      const value = this.$refs.statusResolution.value
      console.log('###', value)
      this.isRefusalReasonVisible =
        ['partially_successful', 'refused'].indexOf(value) > -1
    }
  },
  mounted() {
    this.updateRefusalReasonVisibility()
  }
}
</script>
