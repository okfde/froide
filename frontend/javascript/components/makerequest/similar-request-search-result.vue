<template>
  <!-- adapted from request_item.html -->
  <div class="d-flex mb-4">
    <a
      v-if="object.status_representation"
      :class="`flex-shrink-0 icon status-${object.status_representation} ${'--has-fee' && (object.costs > 0)}`"
      :href="object.url"
      :title="object.readable_status"></a>
    <div class="flex-grow-1 ms-3">
      <!-- cf. foirequest/snippets/request_item_inner.html;
         following comments indicate differences to there -->
      <div>
        <h5 class="mt-0 mb-1">
          <a :href="object.url" target="_blank">{{ object.title }}</a>
          <!-- diff.: object.follower_count omitted -->
        </h5>
        <small>
          <span v-if="object.public_body">
            to {{ object.public_body.name }}<!-- TODO i18n -->
            <!-- diff.: name not link -->
            <span v-if="object.project" class="ms-1">und andere Behörden</span>
            <!-- diff.: und andere not link -->
            <!-- diff./TODO: jurisdiction_name missing, object holds only url a.t.m. -->
            <button type="button" class="btn btn-sm btn-link align-baseline"
              @click="selectPublicBody(object.public_body.id)"
              >
              <!-- TODO i18n -->
              Auch an diese Behörde schreiben
            </button>
          </span>
          <span v-else>
            Not yet set<!-- TODO i18n -->
          </span>
          <br />
          {{ object.readable_status }},
          <!-- diff.: not timesince/"ago", instead "Month YYYY" -->
          <time :datetime="object.last_message">
            {{ formatDate(object.last_message) }}
          </time>
          <!-- diff.: costs omitted -->
          <!-- diff.: same_as_count/identical hint omitted -->
        </small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { useStore } from 'vuex'
import { SET_STEP, STEPS } from '../../store/mutation_types'

const store = useStore()

const pbScope = inject('pbScope')

const { object } = defineProps({
  object: {
    type: Array,
    required: true
  }
})

const selectPublicBody = (id) => {
  store.dispatch('setPublicBodyById', { id, scope: pbScope })
    .then(() => store.commit(SET_STEP, STEPS.WRITE_REQUEST))
    .catch((err) => { console.error('publicbody not found', err) })
}

const formatDate = (date) => (new Date(date)).toLocaleDateString(
  document.documentElement.lang,
  { year: 'numeric', month: 'long' }
)

</script>