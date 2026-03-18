import React, { createContext, useContext, useState, useCallback } from 'react';

/**
 * Live-Region Kontext für barrierefreie Ankündigungen (WCAG 4.1.3)
 * 
 * Ermöglicht es, dynamische Inhaltsänderungen für Screenreader anzukündigen.
 * Unterstützt verschiedene Prioritätsstufen (polite, assertive).
 */

const LiveRegionContext = createContext(null);

export const LiveRegionProvider = ({ children }) => {
  const [politeMessage, setPoliteMessage] = useState('');
  const [assertiveMessage, setAssertiveMessage] = useState('');

  // Ankündigung mit normaler Priorität (wartet, bis Screenreader fertig ist)
  const announcePolite = useCallback((message) => {
    setPoliteMessage('');
    setTimeout(() => setPoliteMessage(message), 100);
  }, []);

  // Dringende Ankündigung (unterbricht aktuelle Ansage)
  const announceAssertive = useCallback((message) => {
    setAssertiveMessage('');
    setTimeout(() => setAssertiveMessage(message), 100);
  }, []);

  // Allgemeine Ankündigungsfunktion
  const announce = useCallback((message, priority = 'polite') => {
    if (priority === 'assertive') {
      announceAssertive(message);
    } else {
      announcePolite(message);
    }
  }, [announcePolite, announceAssertive]);

  return (
    <LiveRegionContext.Provider value={{ announce, announcePolite, announceAssertive }}>
      {children}
      
      {/* Polite Live Region - für normale Ankündigungen */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="live-region"
      >
        {politeMessage}
      </div>
      
      {/* Assertive Live Region - für dringende Ankündigungen */}
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="live-region"
      >
        {assertiveMessage}
      </div>
    </LiveRegionContext.Provider>
  );
};

export const useLiveRegion = () => {
  const context = useContext(LiveRegionContext);
  if (!context) {
    throw new Error('useLiveRegion must be used within a LiveRegionProvider');
  }
  return context;
};

/**
 * Barrierefreier Ladezustand
 */
export const AccessibleLoading = ({ message = "Wird geladen..." }) => {
  return (
    <div role="status" aria-busy="true" aria-live="polite">
      <span className="sr-only">{message}</span>
      <div className="loading-spinner" aria-hidden="true" />
    </div>
  );
};

/**
 * Barrierefreie Fehlermeldung
 */
export const AccessibleError = ({ message, id }) => {
  return (
    <div
      id={id}
      role="alert"
      aria-live="assertive"
      className="form-error bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm"
    >
      {message}
    </div>
  );
};

/**
 * Barrierefreie Erfolgsmeldung
 */
export const AccessibleSuccess = ({ message, id }) => {
  return (
    <div
      id={id}
      role="status"
      aria-live="polite"
      className="form-success bg-green-50 text-green-700 px-4 py-3 rounded-md text-sm"
    >
      {message}
    </div>
  );
};

export default LiveRegionProvider;
