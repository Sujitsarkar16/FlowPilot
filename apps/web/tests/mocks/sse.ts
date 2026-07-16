type Listener = (event: MessageEvent<string>) => void;

export class MockEventSource {
  static instances: MockEventSource[] = [];
  readyState = 1;
  private readonly listeners = new Map<string, Listener[]>();
  constructor(public readonly url: string) { MockEventSource.instances.push(this); }
  addEventListener(type: string, listener: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }
  close() { this.readyState = 2; }
  emit(type: string, data: unknown) {
    for (const listener of this.listeners.get(type) ?? []) listener(new MessageEvent(type, { data: JSON.stringify(data) }));
  }
}

export function installMockEventSource() {
  Object.defineProperty(globalThis, "EventSource", { configurable: true, value: MockEventSource });
}
