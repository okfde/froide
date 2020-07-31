<template>
  <div class="row">
    <div class="col">
      <ul class="nav nav-tabs">
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{'active': tab === 'problemreports'}"
            href="#problemreports"
            @click="tab = 'problemreports'"
          >{{ i18n.problemReports }}</a>
        </li>
        <li
          v-if="publicbodies"
          class="nav-item"
        >
          <a
            class="nav-link"
            :class="{'active': tab === 'publicbodies'}"
            href="#publicbodies"
            @click="tab = 'publicbodies'"
          >
            {{ i18n.publicBodyChangeProposals }}
          </a>
        </li>
      </ul>
      <div class="tab-content pt-3">
        <moderation-problems
          v-if="tab === 'problemreports'"
          :config="config"
          :reports="reports"
        />
        <moderation-publicbodies
          v-if="tab === 'publicbodies'"
          :config="config"
          :publicbodies="publicbodies"
        />
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
import {getData} from '../../lib/api.js'

import ModerationProblems from './moderation-problems.vue'
import ModerationPublicbodies from './moderation-publicbodies.vue'

export default {
  name: 'ModerationDashboard',
  components: {
    ModerationProblems,
    ModerationPublicbodies
  },
  props: {
    config: {
      type: Object,
      required: true
    },
    initialPublicbodies: {
      type: Array,
      required: false,
      default: null
    }
  },
  data () {
    return {
      message: null,
      moderators: [],
      reports: [],
      publicbodies: this.initialPublicbodies,
      filter: {
        mine: false
      },
      tab: 'problemreports'
    }
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
    namedModerators () {
      return this.moderators.filter((m) => m.name !== null)
    },
    remainingModerators () {
      return this.moderators.filter((m) => m.name === null).length
    },
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
        data.report,
        ...this.reports.filter((r) => r.id !== data.report.id)
      ]
    })
    .on('report_updated', (data) => {
      this.reports = this.reports.map((r) => r.id === data.report.id ? data.report : r)
    })
    .on('report_removed', (data) => {
      this.reports = this.reports.filter((r) => r.id !== data.report.id)
    })
    if (this.publicbodies !== null) {
      this.room.on('publicbody_added', (data) => {
        this.publicbodies = [
          data.publicbody,
          ...this.publicbodies.filter((pb) => pb.id !== data.publicbody.id)
        ]
      })
      .on('publicbody_removed', (data) => {
        this.publicbodies = this.publicbodies.filter((pb) => pb.id !== data.publicbody.id)
      })
    }
  },
  methods: {

  }
}
</script>


<style lang="scss" scoped>
  .sidebar {
    position: sticky;
    top: 0;
  }
</style>
