<template>
  <div
    v-if="config.settings.user_can_hide_web && !hasUser"
    class="row mt-2">
    <p>Ihr Name wird als Teil Ihrer Anfrage an die Behörde gesendet. Falls Sie wünschen, dass Ihr Name nicht auf der Website veröffentlicht wrid, können Sie – nach außen hin – anonym bleiben. Ihr Name wrid dann automatisch geschwärzt.</p><!-- TODO i18n -->
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
        >Weitere Infos zur Privatsphäre auf dieser Website</a><!-- TODO i18n -->
    </p>
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