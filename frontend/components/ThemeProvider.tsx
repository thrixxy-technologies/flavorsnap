"use client";
import React, { createContext, useContext, useEffect, useState } from 'react';
import { useTheme as useEnhancedTheme } from '@/hooks/useTheme';

const ThemeContext = createContext<any>(undefined);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const themeState = useEnhancedTheme();

  return (
    <ThemeContext.Provider value={themeState}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    // Fallback to enhanced theme hook
    return useEnhancedTheme();
  }
  return context;
};