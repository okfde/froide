
import "../styles/components/tagautocomplete.scss";

import Choices from "choices.js";

interface IChoicesSearchEvent extends Event { detail: {value: string}; }

function setupTagging() {
  const allSelects = document.querySelectorAll(".tagautocomplete");
  (Array.from(allSelects) as HTMLInputElement[]).forEach((select) => {
    const selectId = select.id.replace("_select", "");
    const realInput = document.querySelector("#" + selectId) as HTMLInputElement;
    if (realInput === null) {
      return;
    }
    const addItemText = select.dataset.additemtext || "";
    const loadingText = select.dataset.loading || "";
    const noResultsText = select.dataset.noresults || "";
    const noChoicesText = select.dataset.nochoices || "";
    const itemSelectText = select.dataset.itemselect || "";
    const uniqueItemText = select.dataset.uniqueitemtext || "";
    const fetchUrl = select.dataset.fetchurl || "";

    const choices = new Choices(select, {
      addItemText(value) {
        return addItemText.replace("${value}", String(value));
      },
      addItems: true,
      classNames: {
        hiddenState: "d-none",
      },
      delimiter: ",",
      duplicateItemsAllowed: false,
      editItems: true,
      itemSelectText,
      loadingText,
      noChoicesText,
      noResultsText,
      removeItemButton: true,
      uniqueItemText,
    });

    select.addEventListener("change", function onchange() {
      choices.hideDropdown();
      const value = choices.getValue(true);
      let valueString;
      if (Array.isArray(value)) {
        valueString = value.join(", ");
      } else {
        valueString = value;
      }
      realInput.value = valueString;
    });

    select.addEventListener("search", function onSearch(event) {
      const choicesEvent = event as IChoicesSearchEvent;
      const value = choicesEvent.detail.value;
      fetch(fetchUrl + "?query=" + encodeURIComponent(value))
      .then((response) => {
        response.json().then((data: string[]) => {
          const present = data.filter((f) => f === value).length > 0;
          const transformed = data.map((x) => ({value: x, label: x}));
          if (!present) {
            transformed.push({value, label: value});
          }
          choices.setChoices(transformed, "value", "label", true);
        });
      });
    });
  });
}

if (document.readyState === "loading") {
  window.document.addEventListener("DOMContentLoaded", setupTagging);
} else {
  setupTagging();
}
