import { Outlet, useLocation, Link } from "react-router-dom";
import AppHeader from "./AppHeader";
import BottomTabBar from "./BottomTabBar";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { pathname } = useLocation();
  const isChat = pathname === "/chat";
  const { appSettings, isLoggedIn, isAdmin } = useAuth();
  const maintenance = Boolean(appSettings?.maintenanceMode);
  const showToolLinks = pathname === "/" || pathname.startsWith("/compare");

  return (
    <div className="app-shell">
      <div className="phone-frame">
        <div className="phone-frame-inner">
          <AppHeader />
          {maintenance && (
            <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs font-medium text-amber-950">
              Maintenance mode is on
              {isAdmin
                ? " — farmers may see limited Ask."
                : ". Ask may be temporarily limited."}
              {isAdmin ? (
                <>
                  {" "}
                  <Link to="/admin" className="underline">
                    Admin settings
                  </Link>
                </>
              ) : null}
            </div>
          )}
          {showToolLinks && (
            <div className="flex gap-2 border-b border-veld-100 bg-white px-3 py-2">
              <Link
                to="/compare"
                className={`rounded-full px-3 py-1 text-[11px] font-semibold ring-1 ${
                  pathname.startsWith("/compare")
                    ? "bg-veld-800 text-white ring-veld-800"
                    : "bg-mist text-veld-800 ring-veld-100"
                }`}
              >
                Compare
              </Link>
              {!isLoggedIn && (
                <Link
                  to="/profile"
                  className="ml-auto rounded-full px-3 py-1 text-[11px] font-semibold text-veld-700"
                >
                  Log in
                </Link>
              )}
            </div>
          )}
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
