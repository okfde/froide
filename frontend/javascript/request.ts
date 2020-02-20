import {toggleSlide} from "./lib/misc";

import {Tab, Tooltip} from "bootstrap.native";

interface IHTMLTabElement extends HTMLElement { Tab: Tab | null; }

const addText = (dataset: DOMStringMap) => {
  if (!dataset.addtextfield) {
    return;
  }
  const textField = document.querySelector(dataset.addtextfield) as HTMLInputElement;
  if (textField === null) {
    return;
  }
  let text = textField.value;
  const addedText = dataset.addtext;
  if (!addedText) {
    return;
  }
  if (text.indexOf(addedText) !== -1) {
    return;
  }
  if (text.indexOf("\n...\n") !== -1) {
    text = text.replace("...", addedText);
  } else {
    const textParts = text.split("\n\n");
    text = [
      textParts[0],
      addedText,
      textParts[textParts.length - 1],
    ].join("\n\n");
    text = textParts.join("\n\n");
  }
  textField.value = text;
};

const setStatus = () => {
  const refusal = document.querySelector(".status-refusal") as HTMLElement;
  if (refusal !== null) {
    refusal.style.display = "none";
    const resolutionElement = document.querySelector("#id_resolution") as HTMLInputElement;
    if (resolutionElement) {
      const resolution = resolutionElement.value;
      if (/refus/.exec(resolution) !== null || /partial/.exec(resolution) !== null) {
        toggleSlide(refusal, 0.5);
      }
    }
  }
};

const runOnPage = () => {
  (Array.from(document.querySelectorAll(".comment-form")) as HTMLElement[]).forEach((el) => {
    el.style.display = "none";
  });

  const requestNav = document.querySelector(".request-nav") as HTMLElement;
  if (requestNav !== null) {
    // let's give the initialization a JavaScript reference for the "target" option
    const tabCollection = requestNav.getElementsByTagName("A");
    Array.from(tabCollection).forEach((tab) => {
      // tslint:disable-next-line: no-unused-expression
      new Tab(tab as HTMLElement, {height: false});
    });
  }

  const idResolution = document.querySelector("#id_resolution");
  if (idResolution !== null) {
    idResolution.addEventListener("change", setStatus);
  }

  const inputStatus = document.querySelector('input[name="status"]');
  if (inputStatus !== null) {
    inputStatus.addEventListener("change", setStatus);
  }

  setStatus();

  const tabLinks = document.querySelectorAll('a[data-tabgo="tab"]');
  Array.from(tabLinks).forEach((tabLink) => {
    tabLink.addEventListener("click", function(this: HTMLElement, e) {
      const hrefAttr = this.attributes.getNamedItem("href");
      if (hrefAttr === null) { return; }
      const href = hrefAttr && hrefAttr.value;
      const el = document.querySelector(href);
      if (el === null) { return; }
      const display = window.getComputedStyle(el, null).display;
      if (display === "none") {
        const navLink = document.querySelector('.nav-link[href="' + href + '"]') as IHTMLTabElement;
        if (navLink && navLink.Tab) {
          navLink.Tab.show();
        }
      }
      if (this.dataset && this.dataset.value) {
        const sel = '[name="' + this.dataset.name + '"][value="' + this.dataset.value + '"]';
        const checkbox = el.querySelector(sel);
        if (checkbox) {
          checkbox.setAttribute("checked", "");
        }
      }
      if (this.dataset && this.dataset.addtextfield) {
        addText(this.dataset);
      }

      if (el.scrollIntoView) {
        e.preventDefault();
        window.setTimeout(() => {
          el.scrollIntoView({behavior: "smooth", block: "start"});
        }, 100);
      }
    });
  });

  if (requestNav !== null) {
    const activeTab = requestNav.dataset.activetab;
    if (activeTab && activeTab !== "info") {
      const activeTabElement = requestNav.querySelector('a[href="#' + activeTab + '"]') as IHTMLTabElement;
      if (activeTabElement && activeTabElement.Tab) {
        activeTabElement.Tab.show();
      }
    } else {
      let hash = document.location && document.location.hash || "";
      hash = hash.replace(/[^#\-\w]/g, "");
      const hashNav = document.querySelector('.request-nav a[href="' + hash + '"]');
      if (hashNav !== null) {
        const tabNav = requestNav.querySelector('a[href="' + hash + '"]') as IHTMLTabElement;
        if (tabNav && tabNav.Tab) {
          tabNav.Tab.show();
        }
      } else if (activeTab !== "info") {
        const tabNav = requestNav.querySelector('a[href="#info"]') as IHTMLTabElement;
        if (tabNav && tabNav.Tab) {
          tabNav.Tab.show();
        }
      }
    }
  }

  interface IMessageOffsetCache { top: number; height: number; id: string; }

  const messages = [] as IMessageOffsetCache[];
  document.querySelectorAll(".message-container").forEach((el) => {
    const rect = el.getBoundingClientRect();
    const offset = rect.top + window.pageYOffset;
    messages.push({
      height: rect.height,
      id: el.id,
      top: offset,
    });
  });
  let activeMessage = null as string | null;
  document.addEventListener("scroll", () => {
    const py = window.pageYOffset;
    for (const message of messages) {
      if (py >= message.top && py <= message.top + message.height) {
        if (activeMessage !== message.id) {
          activeMessage = message.id;
          const navEls = document.querySelectorAll(".message-timeline-listitem a");
          navEls.forEach((el) => {
            el.classList.remove("active");
          });
          const navEl = document.querySelector('.message-timeline-listitem [href="#' + message.id + '"]');
          if (navEl !== null) {
            navEl.classList.add("active");
          }
        }
        break;
      }
    }
  });

  if (!("ontouchstart" in window.document)) {
    Array.from(document.querySelectorAll(".message-timeline-item")).forEach((el) => {
      // tslint:disable-next-line: no-unused-expression
      new Tooltip(el as HTMLElement);
    });
  } else {
    const click = function(this: HTMLElement) {
      this.click();
    };
    Array.from(document.querySelectorAll(".message-timeline-item")).forEach((el) => {
      el.addEventListener("touchstart", click);
    });
  }
};

if (document.readyState === "loading") {
  window.document.addEventListener("DOMContentLoaded", runOnPage);
} else {
  runOnPage();
}
