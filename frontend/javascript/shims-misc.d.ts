declare module "bootstrap.native" {
  export class Tab {
    constructor (el: HTMLElement, options: object);
    show(): void
  }
  export class Tooltip {
    constructor (el: HTMLElement);
    show(): void
  }
}
