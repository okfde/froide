<template>
        <div
          v-if="config.settings.user_can_hide_web && !hasUser"
          class="row mt-2">
          <div class="col-md-8">
            <div class="form-check">
              <input
                id="id_private"
                class="form-check-input"
                v-model="userPrivate"
                type="checkbox"
                name="private" />
              <label for="id_private" class="form-check-label">
                {{ userformFields.private.label }}
              </label>
              <p class="help-block" v-html="userformFields.private.help_text" />
              <p>
                <a
                  :href="config.url.helpRequestPrivacy" 
                  @click.prevent="$emit('online-help', config.url.helpRequestPrivacy)"
                  >§Weitere Infos zur Privatsphäre auf FdS</a>
              </p>
            </div>
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
    initialPrivate: Boolean
  },
  data() {
    return {
      privateValue:
        this.initialPrivate || (this.user && this.user.private) || false
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
        this.$emit('update:initialPrivate', value)
      }
    },
  }
}
</script>