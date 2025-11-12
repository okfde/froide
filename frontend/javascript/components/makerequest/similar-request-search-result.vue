<template>
  <!-- TODO clean this up, provide missing fields -->
  <!-- adapted from request_item.html -->
  <div class="d-flex mb-4">
    <a
      v-if="object.status_representation"
      :class="`flex-shrink-0 icon status-${object.status_representation} ${'--has-fee' && (object.costs > 0)}`"
      :href="object.url"
      :title="object.readable_status"></a>
    <div class="flex-grow-1 ms-3">
      <!-- foirequest/snippets/request_item_inner.html -->
      <div>
        <h5 class="mt-0 mb-1">
          <a :href="object.url">{{ object.title }}</a>
            <!--
            {% if object.follower_count %}
                <span class="badge text-bg-primary ms-2">
                    {% blocktrans count counter=object.follower_count %}
            One follower
          {% plural %}
            {{ counter }} followers
          {% endblocktrans %}
                </span>
            {% endif %}
              -->
        </h5>
        <small>
          <!--
          {% if object.project %}
            {% blocktrans with name=object.public_body.name url=object.public_body.get_absolute_url count=project.request_count|add:-1 urlp=object.project.get_absolute_url %}to <a href="{{ url }}">{{ name }}</a> and <a href="{{ urlp }}">{{ count }} other public bodies</a>{% endblocktrans %}
          {% elif object.public_body_name %}
            {% blocktrans with name=object.public_body_name %}to {{ name }}{% endblocktrans %}
          {% elif object.public_body %}
            {% blocktrans with url=object.public_body.get_absolute_url name=object.public_body.name %}
              <a href="{{ url }}" class="link-secondary">{{ name }}</a>
            {% endblocktrans %}
            – <span class="muted">{{ object.jurisdiction.name }}</span>
          {% else %}
            {% blocktrans %}Not yet set{% endblocktrans %}
          {% endif %}
          -->
          <span v-if="object.project">
            TODO project
          </span>
          <span v-else-if="object.public_body">
            to {{ object.public_body.name }}<!-- TODO i18n -->
            <button type="button" class="btn btn-sm btn-link align-baseline"
              @click="selectPublicBody(object.public_body.id)"
              >
              <!-- TODO i18n -->
              Auch an diese Behörde schreiben
            </button>
            <!--TODO jurisdiction_name?  – <span class="muted">{{ object.jurisdiction.name }}</span>-->
          </span>
          <br />
          {{ object.readable_status }},
          <!-- <span title="{{ object.last_message }}">{% blocktrans with time=object.last_message|timesince %}{{ time }} ago{% endblocktrans %}</span> -->
          <time :datetime="object.last_message">
            {{ object.last_message }}<!-- TODO l10n + ago -->
          </time>
          <!--
          {% if object.costs %}
            ,
            {{ object.costs|floatformat:2 }} {{ froide.currency }}
          {% endif %}
          -->
          <template v-if="object.costs">
            {{ object.costs }} € <!-- TODO floatformat currency -->
          </template>
          <!--
          {% if object.same_as_count %}
            - <a class="muted" href="{{ object.url }}#identical">{% blocktrans with counter=object.same_as_count|intcomma count count=object.same_as_count %}One identical request{% plural %}{{ counter }} identical requests{% endblocktrans %}</a>
          {% endif %}
          -->
        </small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { useStore } from 'vuex'
import { SET_STEP, STEPS } from '../../store/mutation_types'

const store = useStore()

const pbScope = inject('pbScope')

const { object } = defineProps({
  object: {
    type: Array,
    required: true
  }
})

const selectPublicBody = (id) => {
  // TODO catch if 404 + display a warning
  store.dispatch('setPublicBodyById', { id, scope: pbScope })
  store.commit(SET_STEP, STEPS.WRITE_REQUEST)
}

</script>