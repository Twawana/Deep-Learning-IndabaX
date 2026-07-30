import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import Pasture from "./pages/Pasture";
import Weather from "./pages/Weather";
import Profile from "./pages/Profile";
import AdminPanel from "./pages/AdminPanel";
import Scenarios from "./pages/Scenarios";
import Compare from "./pages/Compare";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="pasture" element={<Pasture />} />
          <Route path="weather" element={<Weather />} />
          <Route path="scenarios" element={<Scenarios />} />
          <Route path="compare" element={<Compare />} />
          <Route path="profile" element={<Profile />} />
          <Route path="admin" element={<AdminPanel />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
