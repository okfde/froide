function applyToForm(searchForm: HTMLFormElement) {
  function submitForm() {
    searchForm.submit();
  }
  const inputs = searchForm.querySelectorAll('select, input[type="date"]');
  let i;
  for (i = 0; i < inputs.length; i += 1) {
    const selectInput = inputs[i];
    selectInput.addEventListener("change", submitForm);
  }

  function dropdownSubmit(input: HTMLInputElement) {
    return function(this: HTMLElement, e: Event) {
      e.preventDefault();
      input.value = this.dataset.value || "";
      searchForm.submit();
    };
  }

  const dropdowns = searchForm.querySelectorAll(".dropdown");
  for (i = 0; i < dropdowns.length; i += 1) {
    const dropdown = dropdowns[i];
    const input = dropdown.querySelector("input") as HTMLInputElement;
    const dropdownLinks = dropdown.querySelectorAll(".dropdown-menu a");
    Array.from(dropdownLinks).forEach((dropdownLink) => {
      dropdownLink.addEventListener("click", dropdownSubmit(input));
    });
  }
}

let form = document.querySelector(".search-form") as HTMLFormElement;
if (form !== null) {
  applyToForm(form);
}
