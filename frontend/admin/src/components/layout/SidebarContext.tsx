"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface SidebarContextType {
  isExpanded: boolean;
  setIsExpanded: (val: boolean) => void;
  toggleSidebar: () => void;
  isMounted: boolean;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isExpanded, setIsExpandedState] = useState(true);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const storedValue = localStorage.getItem("sidebar-expanded");
    if (storedValue !== null) {
      setIsExpandedState(storedValue === "true");
    } else {
      // Default to expanded on larger screens (desktop)
      setIsExpandedState(window.innerWidth >= 768);
    }
    setIsMounted(true);
  }, []);

  const setIsExpanded = (val: boolean) => {
    setIsExpandedState(val);
    try {
      localStorage.setItem("sidebar-expanded", String(val));
    } catch (e) {
      console.warn("Failed to save sidebar state to localStorage", e);
    }
  };

  const toggleSidebar = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <SidebarContext.Provider
      value={{
        isExpanded: isMounted ? isExpanded : true, // Fallback to expanded during SSR
        setIsExpanded,
        toggleSidebar,
        isMounted,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}
