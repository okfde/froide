<template>
  <div class="review">
    <div class="row mt-3 mb-3">
      <div class="col-auto">
        <h3 class="display-4">
          {{ i18n._('publicBodiesCount', { count: publicBodies.length }) }}
        </h3>
      </div>
    </div>
    <div class="row">
      <div class="col-auto">
        <button
          class="btn btn-primary"
          @click.prevent="setStepSelectPublicBody">
          &larr; {{ i18n.addMoreAuthorities }}
        </button>
      </div>
      <div class="col-auto ms-auto">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!stepCanContinue(scope)"
          @click="setStepNext"
          >§Weiter</button>
      </div>
    </div>
    <PbSummary
      :scope="scope"
      :i18n="i18n"
      :dimensions="summaryDimensions"></PbSummary>

    <div class="row mb-2">
      <div class="col-auto ms-auto">
        <button
          v-if="publicBodies.length > 0"
          @click.prevent="clearSelection"
          class="btn btn-sm hover-btn-danger">
          <i class="fa fa-ban" aria-hidden="true"></i>
          {{ i18n.clearSelection }}
        </button>
      </div>
    </div>

    <PbTable
      :name="name"
      :scope="scope"
      :i18n="i18n"
      :headers="headers"
      :options="chosenOptions"
      :rows="publicBodies"
      @select-all-rows="selectAllRows"
      class="transition"></PbTable>

    <div class="row">
      <div class="col-auto ms-auto">
        <button
          class="btn btn-primary"
          :disabled="!stepCanContinue(scope)"
          @click="setStepNext"
          >§Weiter</button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapMutations } from 'vuex'
import {
  SET_STEP_NEXT,
  SET_STEP_SELECT_PUBLICBODY
} from '../../store/mutation_types'

import PBChooserMixin from './lib/pb-chooser-mixin'
import PBListMixin from './lib/pb-list-mixin'
import { summaryDimensions } from '../../store/multi_settings'

import PbTable from './pb-table'
import PbSummary from './pb-summary'

export default {
  name: 'PbMultiReview',
  mixins: [PBChooserMixin, PBListMixin],
  props: ['name', 'scope', 'i18n'],
  components: {
    PbTable,
    PbSummary
  },
  data() {
    return {
      chosenOptions: {
        sortableHeader: true
      }
    }
  },
  computed: {
    summaryDimensions() {
      return summaryDimensions
    },
    ...mapGetters([
      'stepCanContinue',
    ])
  },
  methods: {
    ...mapMutations({
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY,
      setStepNext: SET_STEP_NEXT,
    })
  }
}
</script>
