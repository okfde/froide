<template>
  <div>
    <div class="row pb-5">
      <div class="col col-12 col-md-3 text-center text-md-end mb-3 mb-md-0">
        <img
          src="../../../images/make-request/step-intro.avif"
          alt=""
          class="img-lg mb-3 mb-md-0"
        />
      </div>
      <div class="col col-12 col-md-9 order-md-first">
        <h1>{{ i18n.makeRequest }}</h1>
        <p class="lead">{{ i18n.introText }}</p>
        <button class="btn btn-primary arrow-end" @click="emit('stepNext')">
          {{ i18n.letsGo }}
        </button>
      </div>
    </div>
    <div class="border-top border-2 border-light pt-5 mt-3">
      <p>{{ i18n.orCampaign }}</p>
      <div class="mt-4">
        <DjangoSlot name="campaigns" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import DjangoSlot from '../../lib/django-slot.vue'

const i18n = inject('i18n')

defineProps({
  config: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['stepNext'])
</script>
