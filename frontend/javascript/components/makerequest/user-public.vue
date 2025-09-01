<template>
        <div
          v-if="config.settings.user_can_hide_web && !hasUser"
          class="row mt-2">
          <div class="col-md-8">
            <div
              v-for="(choice, choiceIndex) in userformFields.private.choices"
              :key="choice.value"
              class="form-check"
              >
              <input
                :id="'id_private_choice' + choiceIndex"
                class="form-check-input"
                v-model="userPrivate"
                type="radio"
                name="private"
                :value="choice.value"
                />
              <label :for="'id_private_choice' + choiceIndex" class="form-check-label">
                {{ choice.label }}
              </label>
            </div>
            <p class="help-block" v-html="userformFields.private.help_text" />
            <p>
              <a
                :href="config.url.helpRequestPrivacy" 
                @click.prevent="$emit('online-help', config.url.helpRequestPrivacy)"
                >§Weitere Infos zur Privatsphäre auf FdS</a>
            </p>
          </div>
        </div>
</template>

<script>
export default {
  name: 'UserPublic',
  props: {
    config: {
      type: Object
    },
    userForm: {
      type: Object
    },
    initialPrivate: {
      Boolean,
      required: true
    }
  },
  data() {
    return {
      privateValue: this.initialPrivate ? 'True' : 'False'
    }
  },
  computed: {
    userformFields() {
      return this.userForm.fields
    },
    userPrivate: {
      get() {
        return this.privateValue
      },
      set(value) {
        this.privateValue = value
        this.$emit('update:initialPrivate', value === 'True')
      }
    },
  }
}
</script>