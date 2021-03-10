import {scrollToAnchor} from '../lib/misc'

const runOnPage = () => {
  const hideParents = document.querySelectorAll(".hideparent");
  Array.from(hideParents).forEach((hideParent) => {
    hideParent.addEventListener("click", function(this: HTMLElement, e) {
      e.preventDefault();
      const parent = this.parentElement;
      if (parent) {
        parent.style.display = "none";
      }
    });
  });

  /* Set all form submit buttons to disabled on form submit */
  const forms = document.querySelectorAll("form.disable-submit");
  Array.from(forms).forEach((f) => {
    f.addEventListener("submit", function(this: HTMLFormElement) {
      const form = this;
      const buttons = form.querySelectorAll('button[type="submit"]');
      Array.from(buttons).forEach((button) => {
        button.setAttribute("disabled", "");
      });
    });
  });

  const teleports = document.querySelectorAll('[data-teleport]') as NodeListOf<HTMLElement>
  Array.from(teleports).forEach((el) => {
    let location
    if (el.dataset.teleport) {
      location = document.querySelector(el.dataset.teleport)
    } else {
      location = document.body
    }
    if (location) {
      location.appendChild(el)
    }
  })

  const scrollToLinks = document.querySelectorAll("[data-scrollto]") as NodeListOf<HTMLElement>
  Array.from(scrollToLinks).forEach((link) => {
    link.addEventListener('click', (e) => {
      if (link.dataset.scrollto) {
        e.preventDefault()
        scrollToAnchor(link.dataset.scrollto, {
          behavior: 'smooth',
          block: link.dataset.scrolltoblock || 'start'
        })
      }
    })
  });

  const inputs = document.querySelectorAll(".honigtopf input");
  Array.from(inputs).forEach((input) => {
    input.removeAttribute("required");
  });

};

if (document.readyState === "loading") {
  window.document.addEventListener("DOMContentLoaded", runOnPage);
} else {
  runOnPage();
}
