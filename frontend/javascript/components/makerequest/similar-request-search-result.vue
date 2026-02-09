<template>
  <!-- adapted from request_item.html -->
  <div class="d-flex">
    <div class="flex-grow-1">
      <!-- cf. foirequest/snippets/request_item_inner.html;
         following comments indicate differences to there -->
      <div>
        <h3 class="mt-0 mb-1 h5">
          <a :href="object.url" target="_blank">
            {{ object.title }}
            <i class="fa fa-external-link" aria-hidden="true" />
          </a>
          <!-- diff.: object.follower_count omitted -->
        </h3>
        <small>
          <span v-if="object.project">
            {{
              i18n._('searchToProject', {
                name: object.public_body.name,
                count: object.project_request_count
              })
            }}
          </span>
          <span v-else-if="object.public_body_name">{{
            i18n._('searchToPbName', { name: object.public_body_name })
          }}</span>
          <span v-else-if="object.public_body">
            {{ object.public_body.name }}
            <template v-if="showJurisdiction"
              >– {{ object.jurisdiction_name }}</template
            >
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
        </small>
        <div>
          <span class="badge rounded-pill" :class="[statusColorClass]">{{
            object.readable_status
          }}</span>
          <!-- diff.: not timesince/"ago", instead "Month YYYY" -->
          <time :datetime="object.last_message" class="ms-2 small">
            {{ formatDate(object.last_message) }}
          </time>
          <!-- diff.: costs omitted -->
          <!-- diff.: same_as_count/identical hint omitted -->
        </div>
        <div class="small text-secondary mt-1">
          {{ object.description.substring(0, 200) }}
          {{ object.description.length > 200 ? '…' : '' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useStore } from 'vuex'
import { SET_STEP, STEPS } from '../../store/mutation_types'

const store = useStore()

const pbScope = inject('pbScope')

const i18n = inject('i18n')

const props = defineProps({
  object: {
    type: Object,
    required: true
  }
})

const statusColors = {
  awaiting_response: 'text-bg-yellow-200',
  successful: 'text-bg-success',
  partially_successful: 'text-bg-success',
  refused: 'text-bg-danger',
  user_withdrew_costs: 'text-bg-danger'
}

const { object } = props

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

const showJurisdiction = computed(() => {
  return !props.object.public_body.name.includes(props.object.jurisdiction_name)
})

const statusColorClass = computed(
  () => statusColors[props.object.status_representation] ?? 'text-bg-gray-300'
)
</script>
