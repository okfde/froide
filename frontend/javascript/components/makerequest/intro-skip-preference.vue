<template>
  <!-- todo move preference & display it on ähnliche anfragen, too -->
  <div class="form-check my-3" v-if="config.settings.show_skip_intro_howto_preference">
    <input type="checkbox" id="skip_intro_howto" class="form-check-input" v-model="preferenceSkipIntroHowto"
      @change="togglePreference"
      />
    <label for="skip_intro_howto" class="form-check-label">
      Diesen Teil beim nächsten Mal überspringen und direkt mit "Behörde wählen" beginnen (optional)<!-- TODO i18n -->
    </label>
  </div>
  <BsToast v-if="error" color="danger" @dismiss="error = null">
    <template #body>
      {{ error }}
    </template>
  </BsToast>
</template>

<script setup>

import { inject, ref } from 'vue'

import { userpreferenceUpdate } from '../../api'

import BsToast from '../bs-toast.vue'

const i18n = inject('i18n')

const props = defineProps({
  config: {
    type: Object,
    required: true,
  }
})

const preferenceSkipIntroHowto = ref(props.config.settings.skip_intro_howto)
const error = ref()

const togglePreference = () => {
  const toValue = preferenceSkipIntroHowto.value
  const fromValue = !toValue
  preferenceSkipIntroHowto.value = toValue
  userpreferenceUpdate({
    path: { key: props.config.settings.skip_intro_howto_preference_key },
    body: { value: toValue ? "1" : "0" },
    throwOnError: true,
  })
    .catch((err) => {
      console.error('toggle preference error', err)
      preferenceSkipIntroHowto.value = fromValue
      // TODO: err does not have message when 404?
      error.value = `${i18n.error || 'error'} ${err?.message || ''}` // TODO i18n
    })
}

</script>