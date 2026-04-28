import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const SIDEBAR_STORAGE_KEY = "collector-core-admin.sidebar-collapsed";

const navigationItems = [
  {
    to: "/jobs",
    label: "Agendamentos",
    meta: "Fila operacional",
    shortLabel: "AG",
  },
  {
    to: "/beneficios",
    label: "Benefícios",
    meta: "Base persistida",
    shortLabel: "BE",
  },
  {
    to: "/ibge",
    label: "IBGE",
    meta: "Malha territorial",
    shortLabel: "IB",
  },
];

export function AppShell() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const savedValue = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (savedValue === "true") {
      setIsSidebarCollapsed(true);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      String(isSidebarCollapsed),
    );
  }, [isSidebarCollapsed]);

  const currentNavigationItem =
    navigationItems.find((item) => location.pathname.startsWith(item.to)) ??
    navigationItems[0]!;

  return (
    <div
      className={
        isSidebarCollapsed
          ? "app-shell app-shell-sidebar-collapsed"
          : "app-shell"
      }
    >
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="sidebar-brand-mark" aria-hidden="true">
              CC
            </span>
            <div className="sidebar-brand-copy">
              <p className="eyebrow">Collector Core</p>
              <h1>Admin Console</h1>
            </div>
          </div>

          <button
            type="button"
            className="sidebar-toggle"
            aria-label={
              isSidebarCollapsed ? "Expandir menu lateral" : "Colapsar menu lateral"
            }
            onClick={() => setIsSidebarCollapsed((current) => !current)}
          >
            {isSidebarCollapsed ? "›" : "‹"}
          </button>
        </div>

        <div className="brand-block">
          <p className="brand-copy">
            Interface operacional para validar coleta, consultar base e operar agendamentos de coleta.
          </p>
        </div>

        <div className="sidebar-group">
          <span className="sidebar-group-label">Navegação</span>

          <nav className="sidebar-nav" aria-label="Navegação principal">
            {navigationItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                title={item.label}
                className={({ isActive }) =>
                  isActive ? "nav-link nav-link-active" : "nav-link"
                }
              >
                <span className="nav-link-icon" aria-hidden="true">
                  {item.shortLabel}
                </span>
                <span className="nav-link-copy">
                  <strong>{item.label}</strong>
                  <small>{item.meta}</small>
                </span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar-footnote">
          <span className="status-dot" />
          <div className="sidebar-footnote-copy">
            <span>Backend local</span>
            <code>127.0.0.1:8000</code>
          </div>
        </div>
      </aside>

      <main className="content-shell">
        <div className="content-topbar">
          <div className="content-topbar-copy">
            <span className="content-topbar-kicker">Painel</span>
            <strong>{currentNavigationItem.label}</strong>
          </div>
          <div className="content-topbar-meta">
            <span className="content-topbar-chip">Local</span>
            <span className="content-topbar-divider" aria-hidden="true" />
            <code>127.0.0.1:8000</code>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
