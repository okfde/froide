<template>
  <div class="row">
    <div class="col-md-12">
      <input
        type="hidden"
        name="hide_public"
        :value="hidePublic"
        id="id_hide_public" />
      <div class="card mb-3" v-if="!hidePublic">
        <div class="card-body">
          <div>{{ form.fields.public.label }}</div>
          <div
            v-for="(choice, choiceIndex) in form.fields.public.choices"
            :key="choice.value"
            class="form-check"
            >
            <input
              type="radio"
              name="public"
              class="form-check-input"
              :id="'id_public_choice' + choiceIndex"
              :value="choice.value"
              v-model="publicValue"
              />
            <label class="form-check-label" :for="'id_public_choice' + choiceIndex">
              {{ choice.label }}
            </label>
            <!--
            <small class="form-text text-body-secondary">
              {{ form.fields.public.help_text }}
            </small>
            -->
          </div>
        </div>
      </div>
      <div v-else style="display: none">
        <input
          type="checkbox"
          name="public"
          id="id_public"
          v-model="publicValue" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RequestPublic',
  props: {
    form: {
      type: Object
    },
    hidePublic: {
      type: Boolean,
      default: false
    },
    initialPublic: {
      type: Boolean,
      required: true
    },
  },
  data() {
    return {
      public: this.initialPublic ? 'True' : 'False'
    }
  },
  computed: {
    publicValue: {
      get() {
        return this.public
      },
      set(value) {
        this.public = value
        this.$emit('update:initialPublic', value === 'True')
      }
    }
  }
}
</script>
