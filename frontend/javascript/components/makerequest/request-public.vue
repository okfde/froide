<template>
  <div class="row">
    <div class="col-md-12">
      <input
        type="hidden"
        name="hide_public"
        :value="hidePublic"
        id="id_hide_public"
      />
      <div class="mb-3" v-if="!hidePublic">
        <div class="card-body">
          <div
            v-for="(choice, choiceIndex) in form.fields.public.choices"
            :key="choice.value"
            class="form-check form-check-emphasized"
          >
            <input
              type="radio"
              name="public"
              class="form-check-input"
              :id="'id_public_choice' + choiceIndex"
              :value="choice.value"
              v-model="publicValue"
            />
            <label
              class="form-check-label"
              :for="'id_public_choice' + choiceIndex"
              v-html="choice.label"
            />
          </div>
        </div>
      </div>
      <div v-else style="display: none">
        <input
          type="hidden"
          name="public"
          id="id_public"
          v-model="publicValue"
        />
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
      type: String,
      required: true
    }
  },
  data() {
    return {
      public: this.initialPublic
    }
  },
  computed: {
    publicValue: {
      get() {
        return this.public
      },
      set(value) {
        this.public = value
        this.$emit('update:initialPublic', value)
      }
    }
  }
}
</script>
