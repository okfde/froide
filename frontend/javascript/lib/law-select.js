let sortMetaLawsFirst = (a, b) => {
  if (a.meta && !b.meta) return -1
  if (b.meta && !a.meta) return 1

  // 'highest' priority = lowest value
  return a.priority < b.priority
}

let selectBestLaw = (allLaws, lawType) => {
  if (allLaws.length === 0) {
    return null
  }
  let laws = allLaws.filter((l) => {
    return lawType ? l.law_type.indexOf(lawType) !== -1 : true
  })
  if (laws.length === 0) {
    // Fall back to all laws
    laws = [...allLaws]
  }
  laws = laws.sort(sortMetaLawsFirst)
  return laws[0]
}

export {
  selectBestLaw
}
