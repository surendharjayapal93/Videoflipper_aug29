import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// RTL doesn't auto-unmount between tests outside of a supported test
// framework integration; do it explicitly so each test starts from a clean
// DOM tree.
afterEach(() => {
  cleanup();
  localStorage.clear();
});
