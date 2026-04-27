import { Navigate, createBrowserRouter } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { BeneficiosPage } from "../pages/BeneficiosPage";
import { IbgePage } from "../pages/IbgePage";
import { JobsPage } from "../pages/JobsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/jobs" replace />,
      },
      {
        path: "jobs",
        element: <JobsPage />,
      },
      {
        path: "beneficios",
        element: <BeneficiosPage />,
      },
      {
        path: "ibge",
        element: <IbgePage />,
      },
    ],
  },
], {
  basename: "/admin",
});
