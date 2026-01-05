<template>
  <div
    class="row mt-2">
    <div class="col-md-8">
      <p>{{ field.help_text }}</p>
    </div>
  </div>
  <div class="row">
    <div class="col-md-8">
      <div
        v-for="(choice, choiceIndex) in field.choices"
        :key="choice.value"
        class="form-check"
        >
        <input
          :id="'id_claims_vip_choice' + choiceIndex"
          class="form-check-input"
          v-model="value"
          type="radio"
          name="claims_vip"
          :value="choice.value"
          />
        <label :for="'id_claims_vip_choice' + choiceIndex" class="form-check-label" v-html="choice.label" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserClaimsVip',
  props: {
    config: {
      type: Object
    },
    userForm: {
      type: Object
    },
    initialValue: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      internalValue: this.initialValue
    }
  },
  computed: {
    field () {
      return this.userForm.fields.claims_vip
    },
    value: {
      get() {
        return this.internalValue
      },
      set(newValue) {
        this.internalValue = newValue
        this.$emit('update:initialValue', newValue)
      }
    },
  }
}
</script>