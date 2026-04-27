import { NavLink, Outlet } from "react-router-dom";

const navigationItems = [
  { to: "/jobs", label: "Agendamentos de coleta" },
  { to: "/beneficios", label: "Benefícios" },
  { to: "/ibge", label: "IBGE" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Collector Core</p>
          <h1>Admin Console</h1>
          <p className="brand-copy">
            Interface operacional para validar coleta, consultar base e operar agendamentos de coleta.
          </p>
        </div>

        <nav className="sidebar-nav" aria-label="Navegação principal">
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footnote">
          <span className="status-dot" />
          Backend local via proxy em <code>127.0.0.1:8000</code>
        </div>
      </aside>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
