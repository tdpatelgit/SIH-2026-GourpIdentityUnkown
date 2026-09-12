"use client";

import { useEffect } from "react";

/**
 * Fixes the classic "back button shows a protected page after logout"
 * bug: browsers can restore a page from the back-forward cache (bfcache)
 * without re-running React effects, so a stale authenticated render can
 * reappear even after the user has logged out or their session ended.
 *
 * `pageshow`'s `event.persisted === true` is the reliable cross-browser
 * signal for "this page came back from bfcache, not a fresh load/nav".
 * On that signal we force a hard reload so the page's auth-check effect
 * runs again against current session state instead of showing a frozen
 * snapshot.
 */
export function useBfcacheGuard() {
  useEffect(() => {
    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) {
        window.location.reload();
      }
    }
    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
  }, []);
}
