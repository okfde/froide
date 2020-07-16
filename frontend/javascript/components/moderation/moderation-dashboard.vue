<template>
  <div class="row">
    <div class="col">
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
            name="moderation-row"
          >
            <moderation-row
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
    </div>
    <div class="col-auto">
      <div class="sidebar">
        <h5>{{ i18n.activeModerators }}</h5>
        <ul>
          <li
            v-for="moderator in namedModerators"
            :key="moderator.id"
          >
            {{ moderator.name }}
          </li>
          <li v-if="remainingModerators > 0">
            + {{ remainingModerators }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>

import Room from "../../lib/websocket.ts"
import {getData, postData} from '../../lib/api.js'

import ModerationRow from './moderation-row.vue'

const MAX_CLAIM_COUNT = 5
const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationDashboard',
  components: {
    ModerationRow
  },
  props: {
    config: {
      type: Object,
      required: true
    }
  },
  data () {
    return {
      message: null,
      moderators: [],
      reports: [],
      filter: {
        mine: false
      }
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
    namedModerators () {
      return this.moderators.filter((m) => m.name !== null)
    },
    remainingModerators () {
      return this.moderators.filter((m) => m.name === null).length
    },
    claimCount () {
      return this.reports.filter(r => r.moderator_id === this.config.settings.user_id).length
    },
    canClaim () {
      return this.claimCount < MAX_CLAIM_COUNT
    }
  },
  created () {
    this.$root.config = this.config
    this.$root.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value
    this.room = new Room(this.config.url.moderationWebsocket)
    getData(this.config.url.listReports).then((data) => {
      this.reports = [
        ...this.reports,
        ...data.objects
      ]
    })
    this.room.connect()
    .on('userlist', (data) => {
      this.moderators = data.userlist      
    })
    .on('report_added', (data) => {
      this.reports = [
        data,
        ...this.reports.filter((r) => r.id !== data.report.id)
      ]
    })
    .on('report_updated', (data) => {
      this.reports = this.reports.map((r) => r.id === data.report.id ? data.report : r)
    })
    .on('report_removed', (data) => {
      this.reports = this.reports.filter((r) => r.id !== data.report.id)
    })
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
    escalate ({reportId, escalation}) {
      postData(
        getUrl(this.config.url.escalateReport, reportId), {
          escalation
        },
        this.$root.csrfToken
      )
    },
    resolve ({reportId, resolution}) {
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
  .sidebar {
    position: sticky;
    top: 0;
  }
</style>
