<template>
  <div class="row">
    <div class="col-auto col-lg-2 order-lg-2">
      <div class="sidebar">
        <h5>{{ i18n.activeModerators }}</h5>
        <ul>
          <li v-for="moderator in namedModerators" :key="moderator.id">
            {{ moderator.name }}
          </li>
          <li v-if="remainingModerators > 0">+ {{ remainingModerators }}</li>
        </ul>
      </div>
    </div>
    <div class="col col-lg-10 order-lg-1">
      <ul class="nav nav-tabs">
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: tab === 'problemreports' }"
            href="#problemreports"
            @click="tab = 'problemreports'">
            {{ i18n.problemReports }}
            <span class="badge text-bg-secondary">{{
              problemreportsCount
            }}</span>
          </a>
        </li>
        <li v-if="publicbodies" class="nav-item">
          <a
            class="nav-link"
            :class="{ active: tab === 'publicbodies' }"
            href="#publicbodies"
            @click="tab = 'publicbodies'">
            {{ i18n.publicBodyChangeProposals }}
            <span class="badge text-bg-secondary">{{ publicbodiesCount }}</span>
          </a>
        </li>
        <li v-if="unclassified" class="nav-item">
          <a
            class="nav-link"
            :class="{ active: tab === 'unclassified' }"
            href="#unclassified"
            @click="tab = 'unclassified'">
            {{ i18n.unclassifiedRequests }}
            <span class="badge text-bg-secondary">{{ unclassifiedCount }}</span>
          </a>
        </li>
        <li v-if="attachments" class="nav-item">
          <a
            class="nav-link"
            :class="{ active: tab === 'attachments' }"
            href="#attachments"
            @click="tab = 'attachments'">
            {{ i18n.attachments }}
            <span class="badge text-bg-secondary">{{ attachmentsCount }}</span>
          </a>
        </li>
      </ul>
      <div class="tab-content pt-3">
        <moderation-problems
          v-if="tab === 'problemreports'"
          :reports="reports" />
        <moderation-publicbodies
          v-if="tab === 'publicbodies'"
          :publicbodies="publicbodies" />
        <moderation-unclassified
          v-if="tab === 'unclassified'"
          :unclassified="unclassified" />
        <moderation-attachments
          v-if="tab === 'attachments'"
          :attachments="attachments" />
      </div>
    </div>
  </div>
</template>

<script>
import Room from '../../lib/websocket.ts'
import { getData } from '../../lib/api.js'

import ModerationProblems from './moderation-problems.vue'
import ModerationPublicbodies from './moderation-publicbodies.vue'
import ModerationUnclassified from './moderation-unclassified.vue'
import ModerationAttachments from './moderation-attachments.vue'

const MAX_OBJECTS = 100

const showMaxCount = (l) => `${l}${l >= MAX_OBJECTS ? '+' : ''}`

export default {
  name: 'ModerationDashboard',
  components: {
    ModerationProblems,
    ModerationPublicbodies,
    ModerationUnclassified,
    ModerationAttachments
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
    },
    initialUnclassified: {
      type: Array,
      required: false,
      default: null
    },
    initialUnclassifiedCount: {
      type: Number,
      required: false,
      default: null
    },
    initialAttachments: {
      type: Array,
      required: false,
      default: null
    },
    initialAttachmentsCount: {
      type: Number,
      required: false,
      default: null
    }
  },
  data() {
    return {
      message: null,
      moderators: [],
      reports: [],
      publicbodies: this.initialPublicbodies,
      unclassified: this.initialUnclassified,
      unclassifiedCount: this.initialUnclassifiedCount,
      attachments: this.initialAttachments,
      attachmentsCount: this.initialAttachmentsCount,
      filter: {
        mine: false
      },
      tabs: ['problemreports', 'unclassified', 'publicbodies', 'attachments'],
      tab: 'problemreports'
    }
  },
  provide() {
    return {
      config: this.config,
      csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
      room: this.room
    }
  },
  computed: {
    i18n() {
      return this.config.i18n
    },
    namedModerators() {
      return this.moderators.filter((m) => m.name !== null)
    },
    remainingModerators() {
      return this.moderators.filter((m) => m.name === null).length
    },
    problemreportsCount() {
      return this.reports.length
    },
    publicbodiesCount() {
      return showMaxCount(this.publicbodies.length)
    }
  },
  created() {
    this.room = new Room(this.config.url.moderationWebsocket)
    getData(this.config.url.listReports).then((data) => {
      this.reports = [...this.reports, ...data.objects]
    })
    this.room
      .connect()
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
        this.reports = this.reports.map((r) =>
          r.id === data.report.id ? data.report : r
        )
      })
      .on('report_removed', (data) => {
        this.reports = this.reports.filter((r) => r.id !== data.report.id)
      })
    if (this.publicbodies !== null) {
      this.room
        .on('publicbody_added', (data) => {
          this.publicbodies = [
            data.publicbody,
            ...this.publicbodies.filter((pb) => pb.id !== data.publicbody.id)
          ]
        })
        .on('publicbody_removed', (data) => {
          this.publicbodies = this.publicbodies.filter(
            (pb) => pb.id !== data.publicbody.id
          )
          this.reloadData()
        })
    }
    if (this.unclassified !== null) {
      this.room.on('unclassified_removed', (data) => {
        this.unclassified = this.unclassified.filter(
          (fr) => fr.id !== data.unclassified.id
        )
        this.reloadData()
      })
    }
    if (this.attachments !== null) {
      this.room.on('attachment_approved', (data) => {
        this.attachments = this.attachments.filter(
          (at) => at.id !== data.attachments.id
        )
        this.reloadData()
      })
    }
  },
  mounted() {
    const anchor = document.location.hash.substr(1)
    if (this.tabs.includes(anchor)) {
      this.tab = anchor
    }
  },
  methods: {
    reloadData() {
      getData('.').then((data) => {
        this.attachments = data.attachments
        this.attachmentsCount = data.attachments_count
        this.unclassified = data.unclassified
        this.unclassifiedCount = data.unclassified_count
        this.publicbodies = data.publicbodies
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.sidebar {
  position: sticky;
  top: 0;
}
</style>
