<template>
  <div>
    <div class="row mb-3">

      <!-- Text query input -->

      <div class="col col-md-8">
        <input class="form-control" type="text" v-model="textQuery" />
      </div>
      <div class="col col-md-4">
        <button
          type="button"
          class="btn btn-secondary d-block w-100"
          @click="search"
          :disabled="isSearching"
          >
          <!-- TODO i18n -->
          Search
        </button>
      </div>

    </div>

    <div class="row">

      <!-- Dropdown Jurisdiction -->

      <div class="col col-md-3">
        <div class="dropdown">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            >Ebene</button>
          <div
            class="dropdown-menu p-3"
            >
            <ul class="list-unstyled">
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
                  <label
                    :for="regionKind"
                    class="form-check-label"
                    >{{ jurisdictions.name }}</label>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Dropdown Sub-Jurisdiction -->

      <div
        class="col col-md-3"
        v-if="jurisdictionsByRegionKind[jurisdictionRegionKind]?.items.length > 1"
        >
        <div class="dropdown">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            >{{ jurisdictionsByRegionKind[jurisdictionRegionKind].name }}</button>
          <div
            class="dropdown-menu p-3"
            >
            <ul class="list-unstyled">
              <li
                v-for="jurisdiction in jurisdictionsByRegionKind[jurisdictionRegionKind].items"
                :key="jurisdiction.id"
                >
                <div class="form-check">
                  <!--<input
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
                    >{{ jurisdiction.name }}</label>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Dropdown time range -->

      <div class="col col-md-3">
        <div class="dropdown">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            >Zeitraum</button>
          <div class="dropdown-menu p-3">
            <div class="d-sm-flex">
              <!--
              <label for="date_start" class="form-label g-col-sm-4">From</label>
              <input id="date_start" type="date" class="form-control g-col-sm-8" v-model="dateStart" />
              -->
              <select
                class="form-select"
                aria-label="Von"
                v-model="dateStart"
                style="min-width: 10ch"
                >
                <option :value="null"></option>
                <option v-for="year in dateYearsStart" :key="year" :value="year">{{ year }}</option>
              </select>
              <span class="px-1">&mdash;</span>
              <!--
              <label for="date_end" class="form-label g-col-sm-4">To</label>
              <input id="date_end" type="date" class="form-control g-col-sm-8" v-model="dateEnd" />
              -->
              <select
                class="form-select"
                aria-label="Bis"
                v-model="dateEnd"
                style="min-width: 10ch"
                >
                <option :value="null"></option>
                <option v-for="year in dateYearsEnd" :key="year" :value="year">{{ year }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Dropdown Campaign -->

      <div class="col col-md-3">
        <div class="dropdown">
          <button
            type="button"
            class="btn btn-secondary dropdown-toggle d-block w-100"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            >Kampagne</button>
          <div class="dropdown-menu p-3">
            <ul class="list-unstyled">
              <li
                v-for="campaign in campaigns"
                :key="campaign.id"
                >
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
                    >{{ campaign.name }}</label>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

    </div>

    <!-- Active filter badges -->

    <div class="my-3">

      <!-- Badges: Jurisdiction/kind + sub-jurisdiction -->

      <span
        v-if="jurisdictionsByRegionKind[jurisdictionRegionKind]?.items.length === 1 ||
        (jurisdictionRegionKind && jurisdictionsByRegionKind[jurisdictionRegionKind] && selectedJurisdictions.size === 0 && !selectedJurisdiction)"
        class="badge text-bg-secondary"
        >
        {{ jurisdictionsByRegionKind[jurisdictionRegionKind].name }}
        <button
          type="button" class="btn-close"
          @click="jurisdictionRegionKind = null"
          ></button>
      </span>

      <span
        v-for="jurisdiction in selectedJurisdictions"
        :key="jurisdiction.id"
        class="badge text-bg-secondary"
        >
        {{ jurisdiction.name }}
        <button
          type="button" class="btn-close"
          @click="selectedJurisdictions.delete(jurisdiction)"
          ></button>
      </span>

      <span
        v-if="selectedJurisdiction"
        class="badge text-bg-secondary"
        >
        {{ selectedJurisdiction.name }}
        <button
          type="button" class="btn-close"
          @click="selectedJurisdiction = null"
          ></button>
      </span>

      <!-- Badge: campaign -->

      <span
        v-if="selectedCampaign"
        class="badge text-bg-secondary"
        >{{ selectedCampaign.name }}
        <button
          type="button" class="btn-close"
          @click="selectedCampaign = null"
          ></button>
      </span>

      <!-- Badges: from/to year -->

      <span
        v-if="dateStart"
        class="badge text-bg-secondary"
        >Von: {{ dateStart }}
        <button
          type="button" class="btn-close"
          @click="dateStart = null"
          ></button>
      </span>

      <span
        v-if="dateEnd"
        class="badge text-bg-secondary"
        >Bis: {{ dateEnd }}
        <button
          type="button" class="btn-close"
          @click="dateEnd = null"
          ></button>
      </span>

    </div>

    <!-- Results with count + pagination -->

    <div v-if="showResults">
      <p>
        {{ resultsCount }}
        Ergebnisse<!-- TODO i18n -->
      </p>

      <ResultsPagination
        :response-meta="resultsMeta"
        v-model="pagination"
        />

      <ul class="list-unstyled">
        <li v-for="object in results" :key="object.id">
          <SimilarRequestSearchResult :object="object" />
        </li>
      </ul>

      <ResultsPagination
        :response-meta="resultsMeta"
        v-model="pagination"
        />
    </div>

  </div>
</template>

<script setup>
import { computed, ref, reactive, watch } from 'vue'
import { useStore } from 'vuex'
import debounce from 'lodash.debounce'
import { jurisdictionList, campaignList, requestList } from '../../api';
import SimilarRequestSearchResult from './similar-request-search-result.vue';
import ResultsPagination from './results-pagination.vue'
import { UPDATE_SIMILAR_REQUEST_SEARCH } from '../../store/mutation_types'

const props = defineProps({
  minYear: {
    type: Number,
    default: 2014 // TODO
  }
})

const searchResultPageSize = 10

const store = useStore()
const initialState = store.state.similarRequestSearch

const pagination = reactive({
  offset: initialState?.pagination?.offset || 0,
  limit: searchResultPageSize,
})

// hide empty results list on load
const showResults = ref(false)

const textQuery = ref(initialState.textQuery || '')

const jurisdictionRegionKind = ref(initialState.jurisdictionRegionKind)

const jurisdictionsByRegionKind = ref({})

// n.b. new Set!
const selectedJurisdictions = ref(new Set(initialState.selectedJurisdictions))
const selectedJurisdiction = ref(initialState.selectedJurisdiction)

jurisdictionList().then((resp) => {
  // jurisdictionRegionKind.value = resp.data.objects[0].region_kind
  const regionKinds = new Set(resp.data.objects.map((j) => j.region_kind))
  regionKinds.forEach((regionKind) => {
    const items = resp.data.objects.filter((j) => j.region_kind === regionKind)
    regionKind = regionKind || 'root'
    jurisdictionsByRegionKind.value[regionKind] = {
      label: regionKind,
      rank: items[0]?.rank,
      items,
      name: items.length === 1
        ? items[0].name
        : items[0].region_kind_detail // TODO Land vs Bundesland vs Freistaat...
    }
  })
})

const campaigns = ref([])
const selectedCampaign = ref(initialState.selectedCampaign)

campaignList().then((resp) => {
  campaigns.value = resp.data.objects
  // TODO: check if (pre)selectedCampaign exists, and maybe reset
})

const dateStart = ref(initialState.dateStart)
const dateEnd = ref(initialState.dateEnd)

const dateYearsStart = computed(() => Array.from(
  { length: (new Date).getFullYear() - props.minYear },
  (_, y) => y + props.minYear
))

// TODO watch dateStart, push dateEnd if <=
const dateYearsEnd = computed(() => dateStart.value
  ? dateYearsStart.value.filter((y) => y >= dateStart.value)
  : dateYearsStart.value
)

const query = computed(() => ({
  ...pagination,
  ...textQuery.value
    ? { q: textQuery.value }
    : {},
  // jurisdiction: [...selectedJurisdictions.value].map((j) => j.id).join(',')
  ...selectedJurisdictions.value.size > 0
    ? { jurisdiction: [...selectedJurisdictions.value].map((j) => j.id) }
    : {},
  ...selectedJurisdiction.value
    ? { jurisdiction: selectedJurisdiction.value.id }
    : {},
  ...jurisdictionRegionKind.value && !selectedJurisdiction.value
      // ? { jurisdiction_rank: jurisdictionsByRegionKind.value[jurisdictionRegionKind.value].rank }
      ? { jurisdiction: jurisdictionsByRegionKind.value[jurisdictionRegionKind.value]?.items.map((j) => j.id) }
      : {},
  ...jurisdictionRegionKind.value && jurisdictionsByRegionKind.value[jurisdictionRegionKind.value]?.items.length === 1
      ? { jurisdiction: jurisdictionsByRegionKind.value[jurisdictionRegionKind.value]?.items[0].id }
      : {},
  ...selectedCampaign.value ? { campaign: selectedCampaign.value.id } : {},
  ...dateStart.value ? { year__gte: dateStart.value } : {},
  ...dateEnd.value ? { year__lte: dateEnd.value } : {},
}))
// new URLSearchParams...toString

const resultsCount = ref(0)
const resultsMeta = ref({})
const results = ref([])

const isSearching = ref(false)

const search = () => {
  isSearching.value = true
  // FIXME: there are two endpoints
  //  requestSearchRetrieve - has "full text" search `?q=foo`
  //  requestList - doesn't have it
  // this is the main difference; there are other subtle limitations & breakages,
  // main one: search-by-multiple-jurisdictions-OR resp. search-by-jurisdiction-rank
  // and problems with search-by-year
  requestList({
    query: query.value
  })
    .then((resp) => {
      showResults.value = true
      resultsCount.value = resp.data.meta.total_count
      resultsMeta.value = resp.data.meta
      results.value = resp.data.objects
    })
    .finally(() => {
      isSearching.value = false
    })
}

if (initialState.initialSearch) search()

// on query change, rewind pagination
watch(
  [textQuery, selectedJurisdictions, selectedJurisdiction, jurisdictionRegionKind, selectedCampaign, dateStart, dateEnd],
  () => { pagination.offset = 0 }
)
// on query change, including pagination but excluding text, trigger search
watch(
  [pagination, selectedJurisdictions, selectedJurisdiction, jurisdictionRegionKind, selectedCampaign, dateStart, dateEnd],
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
    selectedJurisdictions: [...selectedJurisdictions.value],
    selectedJurisdiction: selectedJurisdiction.value,
    jurisdictionRegionKind: jurisdictionRegionKind.value,
    selectedCampaign: selectedCampaign.value,
    dateStart: dateStart.value,
    dateEnd: dateEnd.value,
    initialSearch: true,
  })
})

</script>