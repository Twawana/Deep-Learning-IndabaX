import { Outlet, useLocation } from "react-router-dom";
import AppHeader from "./AppHeader";
import BottomTabBar from "./BottomTabBar";

export default function Layout() {
  const { pathname } = useLocation();
  const isChat = pathname === "/chat";

  return (
    <div className="app-shell">
      <div className="phone-frame">
        <div className="phone-frame-inner">
          <AppHeader />
          <main
            key={pathname}
            className={`phone-content page-enter ${isChat ? "phone-content-chat" : ""}`}
          >
            <Outlet />
          </main>
          <BottomTabBar />
        </div>
      </div>
    </div>
  );
}
