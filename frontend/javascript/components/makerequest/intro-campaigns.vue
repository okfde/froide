<template>
  <div>
    <div class="row">
      <!-- col-12 is slightly akward on medium viewports but will make sure it is front and center -->
      <div class="col-12 col-md-4 mb-4">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <img
              alt="TODO"
              class="ratio ratio-4x3 placeholder mb-3"
              />
            <h2 class="fs-4 my-auto">{{ i18n.makeRequestYourself }}</h2>
            <div>
              <a
                :href="config.url.helpRequestWhat"
                @click.prevent="emit('onlinehelpClick', config.url.helpRequestWhat)"
                >{{ i18n.whatCanIRequest }}</a><br/>
              <a
                :href="config.url.helpRequestWhatNot"
                @click.prevent="emit('onlinehelpClick', config.url.helpRequestWhatNot)"
                >{{ i18n.whatCanINotRequest }}</a><br/>
            </div>
            hey
            <div class="mt-3">
              <button
                type="button" class="btn btn-primary w-100"
                @click="emit('stepNext')"
                >{{ i18n.makeRequest }}</button>
            </div>
          </div>
        </div>
      </div>
      <slot></slot>
    </div>
  </div>
</template>

<script setup>

import { inject } from 'vue'

const i18n = inject('i18n')

defineProps({
  config: {
    type: Object,
    required: true,
  }
})

const emit = defineEmits('onlinehelpClick', 'stepNext')

</script>