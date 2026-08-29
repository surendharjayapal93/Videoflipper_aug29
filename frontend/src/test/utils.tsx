import { render } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';

interface RenderWithProvidersOptions {
  /** Initial history entry. Defaults to the route the element under test is mounted at. */
  route?: string;
  /** Route path the element under test is mounted at. */
  path?: string;
  /** Extra `<Route>` elements (e.g. a placeholder to assert navigation landed on). */
  extraRoutes?: ReactNode;
}

/**
 * Render a component wrapped in `AuthProvider` + a `MemoryRouter`/`Routes`
 * tree, for components that call `useAuth()` and/or `react-router-dom` hooks
 * (`useNavigate`, `useLocation`, `Link`).
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '/', extraRoutes }: RenderWithProvidersOptions = {},
) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
          {extraRoutes}
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}
