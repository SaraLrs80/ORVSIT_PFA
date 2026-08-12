import { Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AdminDashboard from "./pages/admin/AdminDashboard";
import UtilisateursPage from "./pages/admin/UtilisateursPage";
import SupervisionPage from "./pages/admin/SupervisionPage";
import VueEnsemblePage from "./pages/dashboard/VueEnsemblePage";
import FicheTerritorialePage from "./pages/dashboard/FicheTerritorialePage";
import ComparerPage from "./pages/dashboard/ComparerPage";
import ExplorerPage from "./pages/dashboard/ExplorerPage";
import ProtectedRoute from "./components/ProtectedRoute";
import FicheNouvellePage from "./pages/dashboard/FicheNouvellePage";
import ComparerNouvellePage from "./pages/dashboard/ComparerNouvellePage";
import AssistantPage from "./pages/dashboard/AssistantPage";

// App = la « table des routes » de l'application.
// La route /admin est enveloppée dans <ProtectedRoute> : elle exige un utilisateur
// connecté ayant le rôle "administrateur", sinon on est redirigé vers /login.
function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <VueEnsemblePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/comparer"
        element={
          <ProtectedRoute>
            <ComparerNouvellePage />
          </ProtectedRoute>
        }
      />
      {/* L'ancien écran reste joignable le temps de la comparaison des deux.
          Il sera retiré en même temps que comparer.py et fiche.py. */}
      <Route
        path="/dashboard/comparer-ancien"
        element={
          <ProtectedRoute>
            <ComparerPage />
          </ProtectedRoute>
        }
      />
      {/* Explorer : avec ou sans thème dans l'adresse. Sans thème, la page
          retombe sur la santé — chaque thème garde ainsi son URL propre,
          partageable et compatible avec le bouton Retour du navigateur. */}
      <Route
        path="/dashboard/explorer"
        element={
          <ProtectedRoute>
            <ExplorerPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/explorer/:theme"
        element={
          <ProtectedRoute>
            <ExplorerPage />
          </ProtectedRoute>
        }
      />
      {/* Fiche territoriale : avec ou sans identifiant (par défaut, la 1re province). */}
      <Route
        path="/dashboard/fiche"
        element={
          <ProtectedRoute>
            <FicheNouvellePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/fiche/:territoireId"
        element={
          <ProtectedRoute>
            <FicheNouvellePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/assistant"
        element={
          <ProtectedRoute>
            <AssistantPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="administrateur">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/utilisateurs"
        element={
          <ProtectedRoute requiredRole="administrateur">
            <UtilisateursPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/supervision"
        element={
          <ProtectedRoute requiredRole="administrateur">
            <SupervisionPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
