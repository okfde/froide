<template>
  <div>
    <template v-if="formFields.time">
      <input type="hidden" name="time" :value="formFields.time.initial" />
    </template>
    <template v-if="formFields.phone">
      <div class="mb-3 row d-none honigtopf">
        <label class="col-lg-3 col-form-label" for="id_phone">
          {{ formFields.phone.label }}
        </label>
        <div class="col-lg-9">
          <input
            id="id_phone"
            class="form-control"
            type="text"
            name="phone" />
        </div>
      </div>
    </template>
    <template v-if="formFields.test">
      <div class="mb-3 row">
        <label
          class="col-lg-3 col-form-label"
          :class="{
            'text-danger': errors.test,
            'field-required': formFields.test.required
          }"
          for="id_test">
          {{ formFields.test.label }}
        </label>
        <div class="col-lg-9">
          <input class="form-control" type="text" required name="test" />
          <p class="help-block">
            <span>{{ formFields.test.help_text }}</span>
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'UserConfirmation',
  mixins: [I18nMixin],
  props: {
    form: {
      type: Object
    }
  },
  computed: {
    formFields() {
      return this.form.fields
    },
    errors() {
      if (this.form) {
        return this.form.errors
      }
      return {}
    },
  }
}
</script>