import { mapMutations, mapActions } from 'vuex'
import {
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  SET_USER,
  UPDATE_SUBJECT,
  UPDATE_BODY,
  UPDATE_FULL_TEXT,
  UPDATE_ADDRESS,
  UPDATE_EMAIL,
  UPDATE_PRIVATE,
  UPDATE_SIMILAR_REQUEST_SEARCH,
  UPDATE_REQUEST_PUBLIC,
  UPDATE_LAW_TYPE,
  UPDATE_TERMS,
  SET_CONFIG,
  UPDATE_CONFIRM,
  UPDATE_CLAIMS_VIP
} from '../../../store/mutation_types'

// for TypedChoiceFields (essentialy BooleanFields, but radio),
// we never handle or store (actual JS) Booleans, but strings
// (the alternative would be to avoid TypedChoiceFields,
//  and provide the two choice labels on the Vue side)
const coerceDjangoBool = (booleanOrString) => {
  return booleanOrString === true || booleanOrString === 'True'
    ? 'True'
    : 'False'
}

const StoreValueMixin = {
  methods: {
    initAllStoreValues() {
      // from props
      this.setConfig(this.config)

      // the following initStoreValues intertwine several sources,
      // where "onload values" can come from:
      // - form: via formFields, e.g. after a POST, but also via the ?param=value preset "API"
      // - props: <request-page :param="value">, e.g. publicbodies expanded by make_request
      // - storage: sessionStorage "remembered" values (so they survive an account creation)
      //   explicitly saved on step transition by writeToStorage.
      // the precedence rules are complex, so we make several calls to initStoreValues,
      // with different configurations
      // (instead of supporting several Values, probably a singular initStoreValue
      // would be more readable...)

      // init "regular form values" from storage if not POSTed
      // (not form-submitted, but refreshed, or returned from login)
      // in the case of "preset by GET", e.g. ?subject=foo
      // we still do not ignoreStorage to allow changes (of the presets) to persist
      // -- within the session. In the (unlikely) case of "session reuse"
      // (e.g. abandon draft, open the page with different GETs in the same tab)
      // this could lead to the GET parameters be ignored.
      // We prevent this by tying the storage to a URL-scoped key.
      this.initStoreValues({
        ignoreStorage: this.config.wasPost,
        formFields: this.requestForm.fields,
        formCoerce: {
          public: coerceDjangoBool
        },
        mutationMap: {
          subject: UPDATE_SUBJECT,
          body: UPDATE_BODY,
          full_text: UPDATE_FULL_TEXT, // TODO
          public: UPDATE_REQUEST_PUBLIC
        }
      })

      // law_type only passed by query string, e.g. ?law_type=IFG, so never storage, always form
      this.initStoreValues({
        ignoreStorage: true,
        formFields: this.requestForm.fields,
        mutationMap: {
          law_type: UPDATE_LAW_TYPE
        }
      })

      if (this.userInfo !== null) {
        // user is authenticated...
        // authenticated user fields always set by prop, never form, never storage
        this.initStoreValues({
          ignoreStorage: true,
          // no formFields, always from prop
          propMap: {
            user: this.userInfo
          },
          mutationMap: {
            user: SET_USER
          }
        })
      } else {
        // for anonymous/logged-out users we use storage, or forms if POSTed.
        // note that the "fields" here are stored flatly, not in a .user object,
        // and hence we need individual, per-field mutations.
        // see writeToStorage, reduced, where they are flattened/plucked
        this.initStoreValues({
          ignoreStorage: this.config.wasPost,
          formFields: this.userForm.fields,
          formCoerce: {
            private: coerceDjangoBool,
            claims_vip: coerceDjangoBool
          },
          mutationMap: {
            user_email: UPDATE_EMAIL,
            first_name: UPDATE_FIRST_NAME,
            last_name: UPDATE_LAST_NAME,
            private: UPDATE_PRIVATE,
            address: UPDATE_ADDRESS,
            terms: UPDATE_TERMS,
            claims_vip: UPDATE_CLAIMS_VIP
          }
        })
      }

      // confirm is not a form field, always from storage
      this.initStoreValues({
        mutationMap: {
          confirm: UPDATE_CONFIRM
        }
      })

      // address provided via formField.initial when logged in
      this.initStoreValues({
        ignoreStorage: this.config.wasPost,
        formFields: this.userForm.fields,
        mutationMap: {
          address: UPDATE_ADDRESS
        }
      })

      // search form config (jurisdiction/-kind, year range, campaign) is ephemeral, so always in storage only
      this.initStoreValues({
        mutationMap: {
          similarRequestSearch: UPDATE_SIMILAR_REQUEST_SEARCH
        }
      })
    },
    ...mapMutations({
      setConfig: SET_CONFIG
    }),
    ...mapActions(['initStoreValues'])
  }
}

export default StoreValueMixin
