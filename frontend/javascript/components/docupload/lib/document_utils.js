import {postData, putData, getData} from '../../../lib/api.js'

const deleteAttachment = (doc, config, csrf) => {
  const deleteUrl = config.url.deleteAttachment.replace('/0/', `/${doc.id}/`)
  return postData(deleteUrl, {}, csrf)
}

const approveAttachment = (doc, config, csrf) => {
  const approveUrl = config.url.approveAttachment.replace('/0/', `/${doc.id}/`)
  const attachmentUrl = config.url.getAttachment.replace('/0/', `/${doc.id}/`)
  return postData(approveUrl, {}, csrf).then(() => {
    return getData(attachmentUrl)
  })
}

const createDocument = (doc, config, csrf) => {
  const createDocumentUrl = config.url.createDocument.replace('/0/', `/${doc.id}/`)
  return postData(createDocumentUrl, {}, csrf).then((data) => {
    return getData(data.resource_uri)
  })
}

const updateDocument = (doc, config, csrf, payload) => {
  const updateUrl = doc.attachment.document.resource_uri
  return putData(updateUrl, payload, csrf).then((data) => {
    return getData(updateUrl)
  })
}

const DocumentMixin = {
  methods: {
    updateDocument (payload) {
      this.$emit('docupdated', payload)
      if (payload.deleting) {
        return deleteAttachment(this.document, this.config, this.$root.csrfToken).then((data) => {
          this.$emit('docupdated', null)
        })
      }
      if (payload.approving) {
        return approveAttachment(this.document, this.config, this.$root.csrfToken).then((data) => {
          this.$emit('docupdated', {
            approving: false,
            new: true,
            attachment: data
          })
        })
      }
      if (payload.creatingDocument) {
        return createDocument(this.document, this.config, this.$root.csrfToken).then((data) => {
          this.$emit('docupdated', {
            document: data,
            new: true,
            creatingDocument: false
          })
        })
      }
      if (payload.updatingDocument) {
        return updateDocument(this.document, this.config, this.$root.csrfToken, payload.updatingDocument).then((data) => {
          this.$emit('docupdated', {
            document: data,
            new: true,
            updatingDocument: false
          })
        })
      }
    }
  }
}

export {
  DocumentMixin,
  deleteAttachment,
  approveAttachment,
  createDocument
}
