<template>
  <fieldset
    aria-labelledby="id_private_label"
    aria-describedby="id_private_preamble"
  >
    <div class="row mt-2">
      <div id="id_private_preamble" class="col-md-8">
        <slot></slot>
      </div>
    </div>
    <div class="row">
      <div class="col-md-8">
        <div
          v-for="(choice, choiceIndex) in userformFields.private.choices"
          :key="choice.value"
          class="form-check form-check-emphasized"
        >
          <input
            :id="'id_private_choice' + choiceIndex"
            class="form-check-input"
            v-model="userPrivate"
            type="radio"
            name="private"
            :value="choice.value"
          />
          <label
            :for="'id_private_choice' + choiceIndex"
            class="form-check-label"
            v-html="choice.label"
          />
        </div>
        <!-- <p class="help-block" v-html="userformFields.private.help_text" /> -->
        <p>
          <a
            v-if="config.url.helpRequestPrivacy"
            :href="config.url.helpRequestPrivacy"
            target="_blank"
            >{{ i18n.privacyMoreInfo }}</a
          >
        </p>
      </div>
    </div>
  </fieldset>
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
      type: String,
      required: true
    }
  },
  inject: ['i18n'],
  data() {
    return {
      privateValue: this.initialPrivate
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
    }
  }
}
</script>
