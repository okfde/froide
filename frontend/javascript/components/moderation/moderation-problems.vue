<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ i18n.kind }}</th>
          <th>{{ i18n.date }}</th>
          <th>{{ i18n.message }}</th>
          <th>{{ i18n.description }}</th>
          <th class="action-column">
            {{ i18n.action }}
          </th>
        </tr>
      </thead>
      <tbody
        is="transition-group"
        name="moderation-problem"
      >
        <moderation-problem
          v-for="report in reports"
          :key="report.id"
          :report="report"
          :can-claim="canClaim"
          @claim="claim"
          @unclaim="unclaim"
          @resolve="resolve"
          @escalate="escalate"
        />
      </tbody>
    </table>
  </div>
</template>

<script>
import { postData } from '../../lib/api.js'

import ModerationProblem from './moderation-problem.vue'

const MAX_CLAIM_COUNT = 5
const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationProblems',
  components: {
    ModerationProblem
  },
  props: {
    config: {
      type: Object,
      required: true
    },
    reports: {
      type: Array,
      required: true
    }
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
    filteredReports () {
      return this.reports.filter(r => {
        if (this.filter.mine) {
          return r.moderator_id === this.config.settings.user_id
        }
        return true
      })
    },
    claimCount () {
      return this.reports.filter(r => r.moderator_id === this.config.settings.user_id).length
    },
    canClaim () {
      return this.claimCount < MAX_CLAIM_COUNT
    }
  },
  methods: {
    claim (reportId) {
      if (!this.canClaim) {
        window.alert(this.i18n.maxClaimCount)
        return
      }
      postData(
        getUrl(this.config.url.claimReport, reportId), {},
        this.$root.csrfToken
      )
    },
    unclaim (reportId) {
      postData(
        getUrl(this.config.url.unclaimReport, reportId), {},
        this.$root.csrfToken
      )
    },
    escalate ({ reportId, escalation }) {
      postData(
        getUrl(this.config.url.escalateReport, reportId), {
          escalation
        },
        this.$root.csrfToken
      )
    },
    resolve ({ reportId, resolution }) {
      postData(
        getUrl(this.config.url.resolveReport, reportId), {
          resolution
        },
        this.$root.csrfToken
      )
    }
  }
}
</script>

<style lang="scss" scoped>
  .action-column {
    min-width: 120px;
  }
  .moderation-row-enter-active, .moderation-row-leave-active {
    transition: all 0.5s;
  }
  .moderation-row-enter, .moderation-row-leave-to /* .list-leave-active below version 2.1.8 */ {
    opacity: 0;
    transform: translateX(-100%);
  }
</style>
