<template>
  <div class="review">
    <div class="row mt-3 mb-3">
      <div class="col-auto">
        <h3 class="display-4">
          {{ i18n._('publicBodiesCount', {count: publicBodies.length}) }}
        </h3>
      </div>
    </div>
    <div class="row">
      <div class="col-auto">
        <button class="btn btn-primary btn-lg" @click.prevent="setStepSelectPublicBody">
          &larr; weitere Behörden hinzufügen
        </button>
      </div>
    </div>
    <pb-summary :scope="scope" :i18n="i18n" :dimensions="summaryDimensions"></pb-summary>

    <div class="row mb-2">
      <div class="col-auto ml-auto">
        <button v-if="publicBodies.length > 0" @click.prevent="clearSelection" class="btn btn-sm hover-btn-danger">
          <i class="fa fa-ban" aria-hidden="true"></i>
          {{ i18n.clearSelection }}
        </button>
      </div>
    </div>

    <pb-table :name="name" :scope="scope" :i18n="i18n" :headers="headers"
              :options="chosenOptions" :rows="publicBodies" @selectAllRows="selectAllRows" class="transition"></pb-table>
  </div>
</template>

<script>
import {mapMutations} from 'vuex'
import {
  SET_STEP_SELECT_PUBLICBODY
} from '../../store/mutation_types'

import PBChooserMixin from '../../lib/pb-chooser-mixin'
import I18nMixin from '../../lib/i18n-mixin'
import PBListMixin from '../../lib/pb-list-mixin'
import {summaryDimensions} from '../../store/multi_settings'

import PbTable from './pb-table'
import PbSummary from './pb-summary'


export default {
  name: 'pb-multi-review',
  mixins: [PBChooserMixin, PBListMixin],
  props: ['name', 'scope', 'i18n'],
  components: {
    PbTable,
    PbSummary
  },
  data () {
    return {
      chosenOptions: {
        sortableHeader: true
      },
    }
  },
  computed: {
    summaryDimensions () {
      return summaryDimensions
    }
  },
  methods: {
    ...mapMutations({
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY
    })
  }
}
</script>