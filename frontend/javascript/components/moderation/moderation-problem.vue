<template>
  <tr
    :class="{
      'table-secondary': claimedByOther,
      'table-primary': claimedByMe
    }">
    <td :title="report.kind_label" class="kind-emoji">
      {{ emoji }}
    </td>
    <td :title="report.timestamp">
      {{ report.timestamp | date }}
      <span
        v-if="!report.is_requester && !report.auto_submitted"
        class="badge badge-secondary">
        {{ i18n.isNotRequester }}
      </span>
    </td>
    <td>{{ report.message_subject | truncatechars }}</td>
    <td>
      <template v-if="claimedByMe"> {{ report.description }}<br /> </template>
      <template v-else>
        {{ report.description | truncatechars(120) }}<br />
      </template>

      <a
        :href="report.message_url"
        class="btn btn-light btn-sm"
        target="_blank">
        {{ i18n.toMessage }}
      </a>

      <a
        v-if="showPublicBodyLink"
        class="ml-3 btn btn-light btn-sm"
        :href="publicBodyLink"
        target="_blank">
        {{ i18n.toPublicBody }}
      </a>

      <div v-if="resolving" class="card mt-2">
        <div class="card-body">
          <label v-if="!report.auto_submitted" class="d-block">
            <p>{{ i18n.resolutionDescription }}</p>
            <textarea v-model="resolution" class="form-control" />
          </label>
          <button class="btn btn-success mt-1" @click="resolve">
            {{ i18n.markResolved }}
          </button>
        </div>
      </div>

      <div v-if="escalating" class="card mt-2">
        <div class="card-body">
          <label class="d-block">
            <p>{{ i18n.escalationDescription }}</p>
            <textarea v-model="escalation" class="form-control" />
          </label>
          <button class="btn btn-warning mt-1" @click="escalate">
            {{ i18n.escalate }}
          </button>
        </div>
      </div>
    </td>
    <td>
      <button
        v-if="!report.claimed"
        class="btn btn-sm btn-primary"
        :disabled="!canClaim"
        @click="claim">
        {{ i18n.claim }}
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
            {{ i18n.resolve }}…
          </button>
          <button class="btn btn-warning" @click="startEscalating">
            {{ i18n.escalate }}…
          </button>
          <button class="btn btn-secondary" @click="unclaim">
            {{ i18n.unclaim }}
          </button>
        </div>
      </template>
    </td>
  </tr>
</template>

<script>
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

export default {
  name: 'ModerationRow',
  filters: {
    date: (val) => {
      const d = new Date(val)
      const today = new Date().toLocaleDateString()
      const res = d.toLocaleString()
      if (d.toLocaleDateString() === today) {
        return res.split(',')[1].trim()
      }
      return res
    },
    truncatechars: (val, len = 25) => {
      return val.length > len ? val.substring(0, len) + '…' : val
    }
  },
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
    i18n() {
      return this.$root.config.i18n
    },
    showPublicBodyLink() {
      return (
        this.report.kind === 'message_not_delivered' &&
        this.report.related_publicbody_id
      )
    },
    publicBodyLink() {
      return this.$root.config.url.publicBody.replace(
        /0/,
        this.report.related_publicbody_id
      )
    },
    emoji() {
      return EMOJI_MAPPING[this.report.kind] || ''
    },
    claimedByOther() {
      return !!this.report.claimed && !this.claimedByMe
    },
    claimedByMe() {
      return this.report.moderator_id === this.$root.config.settings.user_id
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
        return this.i18n.claimedMinutesAgo.replace(
          /\{min\}/,
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
