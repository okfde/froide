<template>
  <div>
    <div class="row mb-3">
      <!-- Text query input -->

      <div class="col col-md-9">
        <div class="input-group">
          <input
            class="form-control"
            type="search"
            v-model="textQuery"
            :placeholder="i18n.searchRequests"
          />
          <button
            type="button"
            class="btn btn-secondary"
            @click="search"
            :disabled="isSearching"
          >
            <span class="fa fa-search" aria-hidden="true" />
            {{ i18n.search }}
          </button>
        </div>
      </div>
    </div>

    <div class="row">
      <!-- Dropdown Jurisdiction -->

      <div class="col-sm-3">
        <div class="dropdown my-1 my-sm-0">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
          >
            {{ i18n.level }}
          </button>
          <div class="dropdown-menu p-3">
            <ul class="list-unstyled mb-0">
              <li
                v-for="(jurisdictions, regionKind) in jurisdictionsByRegionKind"
                :key="regionKind"
              >
                <div class="form-check">
                  <input
                    type="radio"
                    :id="regionKind"
                    class="form-check-input"
                    name="regionkind"
                    v-model="jurisdictionRegionKind"
                    :value="regionKind"
                  />
                  <label :for="regionKind" class="form-check-label">{{
                    jurisdictions.name
                  }}</label>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Dropdown Sub-Jurisdiction -->

      <div
        class="col-sm-3"
        v-if="
          jurisdictionsByRegionKind[jurisdictionRegionKind]?.items.length > 1
        "
      >
        <div class="dropdown my-1 my-sm-0">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
          >
            {{ jurisdictionsByRegionKind[jurisdictionRegionKind].name }}
          </button>
          <div class="dropdown-menu p-3">
            <ul class="list-unstyled">
              <li
                v-for="jurisdiction in jurisdictionsByRegionKind[
                  jurisdictionRegionKind
                ].items"
                :key="jurisdiction.id"
              >
                <div class="form-check">
                  <!-- alt: multiple jurisdictions stub
                    <input
                    type="checkbox"
                    :id="'j' + jurisdiction.id"
                    class="form-check-input"
                    name="jurisdiction"
                    :value="jurisdiction"
                    v-model="selectedJurisdictions"
                    />-->
                  <input
                    type="radio"
                    :id="'j' + jurisdiction.id"
                    class="form-check-input"
                    name="jurisdiction"
                    :value="jurisdiction"
                    v-model="selectedJurisdiction"
                  />
                  <label
                    :for="'j' + jurisdiction.id"
                    class="form-check-label"
                    >{{ jurisdiction.name }}</label
                  >
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Dropdown time range -->

      <div class="col-sm-3">
        <div class="dropdown my-1 my-sm-0">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
          >
            {{ i18n.dateRange }}
          </button>
          <div class="dropdown-menu p-3">
            <div class="d-flex flex-column flex-md-row align-items-center">
              <!-- alt: label, date input
              <label for="date_start" class="form-label g-col-sm-4">From</label>
              <input id="date_start" type="date" class="form-control g-col-sm-8" v-model="dateStart" />
              -->
              <select
                class="form-select"
                :aria-label="i18n.dateRangeFrom"
                v-model="dateStart"
                style="min-width: 10ch"
              >
                <option :value="null"></option>
                <option
                  v-for="year in dateYearsStart"
                  :key="year"
                  :value="year"
                >
                  {{ year }}
                </option>
              </select>
              <span class="px-1">&mdash;</span>
              <!-- alt: label, date input
              <label for="date_end" class="form-label g-col-sm-4">To</label>
              <input id="date_end" type="date" class="form-control g-col-sm-8" v-model="dateEnd" />
              -->
              <select
                class="form-select"
                :aria-label="i18n.dateRangeTo"
                v-model="dateEnd"
                style="min-width: 10ch"
              >
                <option :value="null"></option>
                <option v-for="year in dateYearsEnd" :key="year" :value="year">
                  {{ year }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Dropdown Campaign -->

      <div class="col-sm-3">
        <div class="dropdown my-1 my-sm-0">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
          >
            {{ i18n.campaign }}
          </button>
          <div class="dropdown-menu p-3">
            <ul class="list-unstyled mb-0">
              <li v-for="campaign in campaigns" :key="campaign.id">
                <div class="form-check">
                  <input
                    type="radio"
                    :id="'campaign_' + campaign.id"
                    class="form-check-input"
                    name="campaign"
                    :value="campaign"
                    v-model="selectedCampaign"
                  />
                  <label
                    :for="'campaign_' + campaign.id"
                    class="form-check-label"
                    >{{ campaign.name }}</label
                  >
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Active filter badges -->

    <div class="my-3 d-flex flex-wrap gap-2">
      <!-- Badges: Jurisdiction/kind + sub-jurisdiction -->

      <PbFilterBadge
        v-if="
          jurisdictionsByRegionKind[jurisdictionRegionKind]?.items.length ===
            1 ||
          (jurisdictionRegionKind &&
            jurisdictionsByRegionKind[jurisdictionRegionKind] &&
            !selectedJurisdiction)
        "
        class="mb-1"
        @remove-click="jurisdictionRegionKind = null"
        :label="i18n.level"
        :value="jurisdictionsByRegionKind[jurisdictionRegionKind].name"
      />

      <!-- alt
        <PbFilterBadge
          v-if="selectedJurisdictions.size > 0"
          v-for="jurisdiction in selectedJurisdictions"
          :key="jurisdiction.id"
          @remove-click="selectedJurisdictions.delete(jurisdiction)"
          :value="jurisdiction.name"
          :label="'TODO'"
          />
      -->

      <PbFilterBadge
        v-if="selectedJurisdiction"
        class="mb-1"
        @remove-click="selectedJurisdiction = null"
        :label="i18n['groupBy_' + jurisdictionRegionKind]"
        :value="selectedJurisdiction.name"
      />

      <!-- Badges: from/to year -->

      <PbFilterBadge
        v-if="dateStart"
        class="mb-1"
        @remove-click="dateStart = null"
        :label="i18n.dateRangeFrom"
        :value="dateStart"
      />
      <PbFilterBadge
        v-if="dateEnd"
        class="mb-1"
        @remove-click="dateEnd = null"
        :label="i18n.dateRangeTo"
        :value="dateEnd"
      />

      <!-- Badge: campaign -->

      <PbFilterBadge
        v-if="selectedCampaign"
        @remove-click="selectedCampaign = null"
        class="mb-1"
        :label="i18n.campaign"
        :value="selectedCampaign.name"
      />
    </div>

    <!-- API errors -->

    <div v-if="apiError" class="alert alert-danger alert-dismissible">
      <strong>{{ i18n.error }}</strong
      ><br />
      <!-- ugly, but better than nothing? -->
      <small>{{ apiError }}</small>
      <button
        type="button"
        class="btn-close"
        :aria-label="i18n.close"
        @click="apiError = null"
      ></button>
    </div>

    <!-- Results with count + pagination -->

    <div v-if="showResults">
      <p>{{ i18n._('results', { count: resultsCount }) }}</p>

      <ResultsPagination :response-meta="resultsMeta" v-model="pagination" />

      <ul class="list-unstyled">
        <li v-for="object in results" :key="object.id">
          <SimilarRequestSearchResult :object="object" />
        </li>
      </ul>

      <ResultsPagination :response-meta="resultsMeta" v-model="pagination" />
    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, reactive, watch } from 'vue'
import { useStore } from 'vuex'
import debounce from 'lodash.debounce'
import {
  jurisdictionList,
  campaignList,
  requestSearchRetrieve
} from '../../api'
import SimilarRequestSearchResult from './similar-request-search-result.vue'
import ResultsPagination from './results-pagination.vue'
import { UPDATE_SIMILAR_REQUEST_SEARCH } from '../../store/mutation_types'
import PbFilterBadge from '../publicbody/pb-filter-badge.vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  }
})

const i18n = inject('i18n')

const searchResultPageSize = 10

const store = useStore()
const initialState = store.state.similarRequestSearch

const pagination = reactive({
  offset: initialState?.pagination?.offset || 0,
  limit: searchResultPageSize
})

// hide empty results list on load
const showResults = ref(false)

const textQuery = ref(initialState.textQuery || '')

const jurisdictionRegionKind = ref(initialState.jurisdictionRegionKind)

const jurisdictionsByRegionKind = ref({})

const selectedJurisdiction = ref(initialState.selectedJurisdiction)

// n.b. new Set! alt: multiple selectable, currently unused
// const selectedJurisdictions = ref(new Set(initialState.selectedJurisdictions))

watch(jurisdictionRegionKind, () => {
  // selectedJurisdictions.value.clear()
  selectedJurisdiction.value = null
})

// populate by fetching from API...
jurisdictionList().then((resp) => {
  const regionKinds = new Set(resp.data.objects.map((j) => j.region_kind))
  regionKinds.forEach((regionKind) => {
    const items = resp.data.objects.filter((j) => j.region_kind === regionKind)
    regionKind = regionKind || 'root'
    jurisdictionsByRegionKind.value[regionKind] = {
      label: regionKind,
      rank: items[0]?.rank,
      items,
      slug: items[0]?.slug,
      name:
        items.length === 1
          ? items[0].name
          : // TODO works out because of alphabetical implicit sorting,
            //   but might end up weird: Land vs Bundesland vs Freistaat...
            items[0].region_kind_detail
    }
  })
})

const campaigns = ref([])
const selectedCampaign = ref(initialState.selectedCampaign)

campaignList().then((resp) => {
  campaigns.value = resp.data.objects
})

const dateStart = ref(initialState.dateStart)
const dateEnd = ref(initialState.dateEnd)

// create ranges for the select-options
const dateYearsStart = computed(() =>
  Array.from(
    { length: new Date().getFullYear() - props.config.settings.min_year + 1 },
    (_, y) => y + props.config.settings.min_year
  )
)
const dateYearsEnd = computed(() =>
  dateStart.value
    ? dateYearsStart.value.filter((y) => y >= dateStart.value)
    : dateYearsStart.value
)

// avoid impossible time ranges, push dateEnd after dateStart if necessary
watch(dateStart, () => {
  if (dateEnd.value === null) return
  if (dateStart.value > dateEnd.value) {
    dateEnd.value = dateStart.value
  }
})

const query = computed(() => {
  const query = { ...pagination }
  if (textQuery.value) {
    query.q = textQuery.value
  }
  // if (selectedJurisdictions.value.size > 0) {
  //  query.jurisdiction = [...selectedJurisdictions.value].map((j) => j.slug)
  // } else
  if (selectedJurisdiction.value) {
    query.jurisdiction = selectedJurisdiction.value.slug
  } else if (
    jurisdictionRegionKind.value &&
    jurisdictionsByRegionKind.value[jurisdictionRegionKind.value]?.items
      .length === 1
  ) {
    // optionally chaining here because jurisdictionList might be still loading (when loaded from storage)
    query.jurisdiction =
      jurisdictionsByRegionKind.value[
        jurisdictionRegionKind.value
      ]?.items[0].slug
  } else if (jurisdictionRegionKind.value && !selectedJurisdiction.value) {
    query.jurisdiction_rank =
      jurisdictionsByRegionKind.value[jurisdictionRegionKind.value]?.rank
  }
  if (selectedCampaign.value) {
    query.campaign = selectedCampaign.value.slug
  }
  if (dateStart.value) {
    query.last_after = dateStart.value + '-01-01'
  }
  if (dateEnd.value) {
    query.first_before = dateEnd.value + '-12-31'
  }
  return query
})

const resultsCount = ref(0)
const resultsMeta = ref({})
const results = ref([])

const isSearching = ref(false)
const apiError = ref(null)

const search = () => {
  isSearching.value = true
  requestSearchRetrieve({
    query: query.value,
    throwOnError: true
  })
    .then((resp) => {
      showResults.value = true
      resultsCount.value = resp.data.meta.total_count
      resultsMeta.value = resp.data.meta
      results.value = resp.data.objects
    })
    .catch((err) => {
      apiError.value = err
    })
    .finally(() => {
      isSearching.value = false
    })
}

if (initialState.initialSearch) search()

// on query change, rewind pagination
watch(
  [
    textQuery,
    // selectedJurisdictions,
    selectedJurisdiction,
    jurisdictionRegionKind,
    selectedCampaign,
    dateStart,
    dateEnd
  ],
  () => {
    pagination.offset = 0
  }
)
// on query change, including pagination but excluding text, trigger search
watch(
  [
    pagination,
    // selectedJurisdictions,
    selectedJurisdiction,
    jurisdictionRegionKind,
    selectedCampaign,
    dateStart,
    dateEnd
  ],
  () => search()
)
// on text query change, trigger debounced
const debouncedSearch = debounce(search, 1000)
watch(textQuery, () => debouncedSearch())
// on query change, persist to storage
watch(query, () => {
  store.commit(UPDATE_SIMILAR_REQUEST_SEARCH, {
    pagination,
    textQuery: textQuery.value,
    // n.b. serializing a Set here!
    // selectedJurisdictions: [...selectedJurisdictions.value],
    selectedJurisdiction: selectedJurisdiction.value,
    jurisdictionRegionKind: jurisdictionRegionKind.value,
    selectedCampaign: selectedCampaign.value,
    dateStart: dateStart.value,
    dateEnd: dateEnd.value,
    initialSearch: true
  })
})
</script>
