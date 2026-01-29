<template>
  <!-- adapted from request_item.html -->
  <div class="d-flex mb-4">
    <a
      v-if="object.status_representation"
      :class="`flex-shrink-0 icon status-${object.status_representation} ${'--has-fee' && object.costs > 0}`"
      :href="object.url"
      :title="object.readable_status"
    ></a>
    <div class="flex-grow-1 ms-3">
      <!-- cf. foirequest/snippets/request_item_inner.html;
         following comments indicate differences to there -->
      <div>
        <h5 class="mt-0 mb-1">
          <a :href="object.url" target="_blank">{{ object.title }}</a>
          <!-- diff.: object.follower_count omitted -->
        </h5>
        <small>
          <span
            v-if="object.project"
            v-html="
              i18n._('searchToProject', {
                name: object.public_body.name,
                url: object.public_body.site_url,
                urlp: object.project_site_url,
                count: object.project_request_count
              })
            "
          />
          <span v-else-if="object.public_body_name">{{
            i18n._('searchToPbName', { name: object.public_body_name })
          }}</span>
          <span v-else-if="object.public_body">
            {{ i18n.to }}
            <a :href="object.public_body.site_url">{{
              object.public_body.name
            }}</a>
            – {{ object.jurisdiction_name }}
          </span>
          <span v-else>
            {{ i18n.notYetSet }}
          </span>
          <button
            v-if="object.public_body.id"
            type="button"
            class="btn btn-sm btn-link align-baseline text-start"
            @click="selectPublicBody(object.public_body.id)"
          >
            {{ i18n.searchSelectThisPb }}
          </button>
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

const i18n = inject('i18n')

const { object } = defineProps({
  object: {
    type: Object,
    required: true
  }
})

const selectPublicBody = (id) => {
  store
    .dispatch('setPublicBodyById', { id, scope: pbScope })
    .then(() => store.commit(SET_STEP, STEPS.WRITE_REQUEST))
    .catch((err) => {
      console.error('publicbody not found', err)
    })
}

const formatDate = (date) =>
  new Date(date).toLocaleDateString(document.documentElement.lang, {
    year: 'numeric',
    month: 'long'
  })
</script>
