const summaryDimensions = [
  {
    id: 'jurisdiction',
    i18nLabel: 'jurisdictionPlural',
    key: (x) => x.jurisdiction.name
  },
  {
    id: 'classification',
    i18nLabel: 'classificationPlural',
    key: (x) => x.classification && x.classification.name
  },
  {
    id: 'categories',
    i18nLabel: 'topicPlural',
    multi: true,
    key: (x) => x.categories.map((x) => x.name)
  }
]

export {
  summaryDimensions
}
