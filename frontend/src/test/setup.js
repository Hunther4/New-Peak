import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

const store = new Map()
const mockStorage = {
  getItem: vi.fn((k) => store.get(String(k)) ?? null),
  setItem: vi.fn((k, v) => { store.set(String(k), String(v)) }),
  removeItem: vi.fn((k) => { store.delete(String(k)) }),
  clear: vi.fn(() => { store.clear() }),
  key: vi.fn((i) => Array.from(store.keys())[i] ?? null),
  get length() { return store.size },
}

Object.defineProperty(window, 'localStorage', {
  value: mockStorage,
  writable: true,
  configurable: true,
})
Object.defineProperty(globalThis, 'localStorage', {
  value: mockStorage,
  writable: true,
  configurable: true,
})
if (typeof Storage !== 'undefined') {
  Storage.prototype.getItem = mockStorage.getItem
  Storage.prototype.setItem = mockStorage.setItem
  Storage.prototype.removeItem = mockStorage.removeItem
  Storage.prototype.clear = mockStorage.clear
}
