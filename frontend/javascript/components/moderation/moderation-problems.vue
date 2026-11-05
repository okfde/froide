<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ gettext('Kind') }}</th>
          <th>{{ gettext('Date') }}</th>
          <th>{{ gettext('Message') }}</th>
          <th>{{ gettext('Description') }}</th>
          <th class="action-column">
            {{ pgettext('action to take in moderation table', 'Action') }}
          </th>
        </tr>
      </thead>
      <TransitionGroup tag="tbody" name="moderation-problem">
        <ModerationProblem
          v-for="report in reports"
          :key="report.id"
          :report="report"
          :can-claim="canClaim"
          @claim="claim"
          @unclaim="unclaim"
          @resolve="resolve"
          @escalate="escalate"
        />
      </TransitionGroup>
    </table>
  </div>
</template>

<script>
import { postData } from '../../lib/api.js'
import { translateMixin } from 'vuepo/vue'

import ModerationProblem from './moderation-problem.vue'

const MAX_CLAIM_COUNT = 5
const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationProblems',
  mixins: [translateMixin],
  components: {
    ModerationProblem
  },
  props: {
    reports: {
      type: Array,
      required: true
    }
  },
  inject: ['config', 'csrfToken'],
  computed: {
    filteredReports() {
      return this.reports.filter((r) => {
        if (this.filter.mine) {
          return r.moderator_id === this.config.settings.user_id
        }
        return true
      })
    },
    claimCount() {
      return this.reports.filter(
        (r) => r.moderator_id === this.config.settings.user_id
      ).length
    },
    canClaim() {
      return this.claimCount < MAX_CLAIM_COUNT
    }
  },
  methods: {
    claim(reportId) {
      if (!this.canClaim) {
        window.alert(
          this.gettext(
            'You cannot work on more than 5 issues at the same time.'
          )
        )
        return
      }
      postData(
        getUrl(this.config.url.claimReport, reportId),
        {},
        this.csrfToken
      )
    },
    unclaim(reportId) {
      postData(
        getUrl(this.config.url.unclaimReport, reportId),
        {},
        this.csrfToken
      )
    },
    escalate({ reportId, escalation }) {
      postData(
        getUrl(this.config.url.escalateReport, reportId),
        {
          escalation
        },
        this.csrfToken
      )
    },
    resolve({ reportId, resolution }) {
      postData(
        getUrl(this.config.url.resolveReport, reportId),
        {
          resolution
        },
        this.csrfToken
      )
    }
  }
}
</script>

<style lang="scss" scoped>
.action-column {
  min-width: 120px;
}
.moderation-row-enter-active,
.moderation-row-leave-active {
  transition: all 0.5s;
}
.moderation-row-enter, .moderation-row-leave-to /* .list-leave-active below version 2.1.8 */ {
  opacity: 0;
  transform: translateX(-100%);
}
</style>
