declare module "bootstrap.native/dist/bootstrap-native-v4" {
  export class Tab {
    constructor (el: HTMLElement, options: object);
    show(): void
  }
  export class Tooltip {
    constructor (el: HTMLElement);
    show(): void
  }
}
