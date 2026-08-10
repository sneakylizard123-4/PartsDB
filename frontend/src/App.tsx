import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { ToastProvider } from "./components/ui";
import { LoginRedirectGuard } from "./components/SearchBar";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Parts from "./pages/Parts";
import NewPart from "./pages/NewPart";
import PartDetail from "./pages/PartDetail";
import Inventory from "./pages/Inventory";
import Transactions from "./pages/Transactions";
import Locations from "./pages/Locations";
import LocationDetail from "./pages/LocationDetail";
import Projects from "./pages/Projects";
import ProjectDetail from "./pages/ProjectDetail";
import ShoppingLists from "./pages/ShoppingLists";
import Organizers from "./pages/Organizers";
import Settings from "./pages/Settings";

function GuardedLayout() {
  return (
    <LoginRedirectGuard>
      <Layout />
    </LoginRedirectGuard>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<GuardedLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/parts" element={<Parts />} />
          <Route path="/parts/new" element={<NewPart />} />
          <Route path="/parts/:id" element={<PartDetail />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/locations" element={<Locations />} />
          <Route path="/locations/:id" element={<LocationDetail />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/shopping" element={<ShoppingLists />} />
          <Route path="/organizers" element={<Organizers />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}
