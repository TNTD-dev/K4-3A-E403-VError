import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import HomePage from "./home.jsx";
import ReaderPage from "./reader.jsx";

function readRoute() {
  const params = new URLSearchParams(window.location.search);
  const day = params.get("day");
  if (!day) return { screen: "home" };
  return { screen: "reader", day: day.toUpperCase(), page: Number(params.get("page")) || 1 };
}

function App() {
  const [route, setRoute] = useState(readRoute);

  useEffect(() => {
    const onPop = () => setRoute(readRoute());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  function openDay(day) {
    window.history.pushState(null, "", `?day=${day}`);
    setRoute({ screen: "reader", day, page: 1 });
    window.scrollTo(0, 0);
  }

  function goHome() {
    window.history.pushState(null, "", window.location.pathname);
    setRoute({ screen: "home" });
    window.scrollTo(0, 0);
  }

  return route.screen === "reader" ? (
    <ReaderPage key={route.day} day={route.day} initialPage={route.page} onBack={goHome} onOpenDay={openDay} />
  ) : (
    <HomePage onOpenDay={openDay} />
  );
}

createRoot(document.getElementById("root")).render(<App />);
