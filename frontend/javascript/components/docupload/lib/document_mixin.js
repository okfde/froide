import {postData, getData} from '../../../lib/api.js'

export default {
  methods: {
    updateDocument (payload) {
      if (payload.deleting) {
        postData(this.deleteUrl, {}, this.$root.csrfToken).then((data) => {
          this.$emit('docupdated', null)
        })
      }
      if (payload.approving) {
        postData(this.approveUrl, {}, this.$root.csrfToken).then(() => {
          getData(this.attachmentUrl).then((data) => {
            this.$emit('docupdated', {
              approving: false,
              attachment: data
            })
          })
        })
      }
      this.$emit('docupdated', payload)
    }
  }
}
