<script setup>
import { useGettext } from 'vuepo/vue'
import DjangoSlot from '../../lib/django-slot.vue'

const { gettext } = useGettext()

defineProps({
  config: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['stepNext'])
</script>

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
        <h1>{{ gettext('Make request') }}</h1>
        <p class="lead">
          {{
            gettext(
              "Access information by filing a request to a public body. We'll guide you through the process."
            )
          }}
        </p>
        <button class="btn btn-primary arrow-end" @click="emit('stepNext')">
          {{ gettext("Let's go!") }}
        </button>
      </div>
    </div>
    <div class="border-top border-2 border-light pt-5 mt-3">
      <p>
        {{
          gettext(
            'Or send a pre-written request with just one click, by participating in one of our campaigns:'
          )
        }}
      </p>
      <div class="mt-4">
        <DjangoSlot name="campaigns" />
      </div>
    </div>
  </div>
</template>
