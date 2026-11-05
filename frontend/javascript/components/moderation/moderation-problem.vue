<template>
  <tr
    :class="{
      'table-secondary': claimedByOther,
      'table-primary': claimedByMe
    }"
  >
    <td :title="report.kind_label" class="kind-emoji">
      {{ emoji }}
    </td>
    <td :title="report.timestamp">
      {{ reportTimestampFormatted }}
      <span
        v-if="!report.is_requester && !report.auto_submitted"
        class="badge text-bg-secondary"
      >
        {{ gettext('not requester') }}
      </span>
    </td>
    <td>{{ reportMessageSubjectTruncated }}</td>
    <td>
      <template v-if="claimedByMe"> {{ report.description }}<br /> </template>
      <template v-else>
        {{ reportDescriptionTruncated }}
        <br />
      </template>

      <a
        :href="report.message_url"
        class="btn btn-outline-secondary btn-sm"
        target="_blank"
      >
        {{ gettext('to message') }}
      </a>

      <a
        v-if="showPublicBodyLink"
        class="ms-3 btn btn-outline-secondary btn-sm"
        :href="publicBodyLink"
        target="_blank"
      >
        {{ gettext('to public body') }}
      </a>

      <div v-if="resolving" class="card mt-2">
        <div class="card-body">
          <label v-if="!report.auto_submitted" class="d-block">
            <p>{{ gettext('Please write a nice message to the user.') }}</p>
            <textarea v-model="resolution" class="form-control" />
          </label>
          <button class="btn btn-success mt-1" @click="resolve">
            {{ gettext('Mark resolved') }}
          </button>
        </div>
      </div>

      <div v-if="escalating" class="card mt-2">
        <div class="card-body">
          <label class="d-block">
            <p>
              {{ gettext('Please describe to admins what should be done.') }}
            </p>
            <textarea v-model="escalation" class="form-control" />
          </label>
          <button class="btn btn-warning mt-1" @click="escalate">
            {{ gettext('Escalate') }}
          </button>
        </div>
      </div>
    </td>
    <td>
      <button
        v-if="!report.claimed"
        class="btn btn-sm btn-primary"
        :disabled="!canClaim"
        @click="claim"
      >
        {{ gettext('Claim') }}
      </button>
      <template v-if="claimedByOther">
        <small :class="{ 'text-danger': longClaim }">
          <time :title="report.claimed">
            {{ claimedMinutesAgo }}
          </time>
        </small>
      </template>
      <template v-if="claimedByMe">
        <div class="btn-group-vertical btn-group-sm">
          <button class="btn btn-success" @click="startResolving">
            {{ gettext('Resolve') }}…
          </button>
          <button class="btn btn-warning" @click="startEscalating">
            {{ gettext('Escalate') }}…
          </button>
          <button class="btn btn-secondary" @click="unclaim">
            {{ gettext('Cancel') }}
          </button>
        </div>
      </template>
    </td>
  </tr>
</template>

<script>
import { translateMixin } from 'vuepo/vue'

const EMOJI_MAPPING = {
  message_not_delivered: '📭',
  bounce_publicbody: '🤖',
  attachment_broken: '📃',
  redaction_needed: '🔏',
  foi_help_needed: '🥺',
  other: '❓',
  not_nice: '💩',
  info_outdated: '⌛️',
  info_wrong: '❌'
}

const MAX_CLAIMED_MINUTES = 15

const calcMinutesAgo = (val) => {
  const now = new Date().getTime()
  const t = new Date(val).getTime()
  return Math.round((now - t) / (1000 * 60))
}

const truncatechars = (val, len = 25) => {
  return val.length > len ? val.substring(0, len) + '…' : val
}

const formatDate = (val) => {
  const d = new Date(val)
  const today = new Date().toLocaleDateString()
  const res = d.toLocaleString()
  if (d.toLocaleDateString() === today) {
    return res.split(',')[1].trim()
  }
  return res
}

export default {
  name: 'ModerationRow',
  mixins: [translateMixin],
  props: {
    report: {
      type: Object,
      required: true
    },
    canClaim: {
      type: Boolean,
      default: true
    }
  },
  inject: ['config'],
  emits: ['claim', 'unclaim', 'resolve', 'escalate'],
  data() {
    return {
      resolving: false,
      resolution: '',
      escalating: false,
      escalation: '',
      claimedTimeAgo: null
    }
  },
  computed: {
    showPublicBodyLink() {
      return (
        this.report.kind === 'message_not_delivered' &&
        this.report.related_publicbody_id
      )
    },
    publicBodyLink() {
      return this.config.url.publicBody.replace(
        /0/,
        this.report.related_publicbody_id
      )
    },
    reportTimestampFormatted() {
      return formatDate(this.report.timestamp)
    },
    reportMessageSubjectTruncated() {
      return truncatechars(this.report.message_subject)
    },
    reportDescriptionTruncated() {
      return truncatechars(this.report.description, 120)
    },
    emoji() {
      return EMOJI_MAPPING[this.report.kind] || ''
    },
    claimedByOther() {
      return !!this.report.claimed && !this.claimedByMe
    },
    claimedByMe() {
      return this.report.moderator_id === this.config.settings.user_id
    },
    longClaim() {
      return this.claimedMinutes > MAX_CLAIMED_MINUTES
    },
    claimedMinutes() {
      if (this.report.claimed) {
        return calcMinutesAgo(this.report.claimed)
      }
      return -1
    },
    claimedMinutesAgo() {
      if (this.report.claimed) {
        return this.gettext('Claimed for {min} min.').replace(
          '{min}',
          this.claimedMinutes
        )
      }
      return ''
    }
  },
  methods: {
    claim() {
      this.$emit('claim', this.report.id)
    },
    unclaim() {
      this.resolving = false
      this.escalating = false
      this.$emit('unclaim', this.report.id)
    },
    startResolving() {
      this.escalating = false
      this.resolving = !this.resolving
    },
    resolve() {
      this.$emit('resolve', {
        reportId: this.report.id,
        resolution: this.resolution
      })
    },
    startEscalating() {
      this.resolving = false
      this.escalating = !this.escalating
    },
    escalate() {
      this.$emit('escalate', {
        reportId: this.report.id,
        escalation: this.escalation
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.kind-emoji {
  cursor: help;
}
</style>
