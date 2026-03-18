/**
 * Barrierefreiheits-Komponenten und Utilities
 * 
 * BITV 2.0 / WCAG 2.1 Konformität
 * 
 * Enthält:
 * - SkipLink: Zum Hauptinhalt springen
 * - LiveRegion: Dynamische Ankündigungen für Screenreader
 * - Fokus-Management Utilities
 * - ARIA-Hilfsfunktionen
 */

export { SkipLink, SkipLinks } from './SkipLink';
export { 
  LiveRegionProvider, 
  useLiveRegion, 
  AccessibleLoading, 
  AccessibleError, 
  AccessibleSuccess 
} from './LiveRegion';

/**
 * Fokus auf ein Element setzen (für Dialog-Management)
 */
export const focusElement = (elementOrId) => {
  const element = typeof elementOrId === 'string' 
    ? document.getElementById(elementOrId) 
    : elementOrId;
  
  if (element) {
    element.focus();
    return true;
  }
  return false;
};

/**
 * Fokus innerhalb eines Containers halten (Fokus-Trap für Dialoge)
 */
export const trapFocus = (containerElement) => {
  const focusableElements = containerElement.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
    
    if (e.key === 'Escape') {
      // Escape-Taste zum Schließen von Dialogen
      const closeButton = containerElement.querySelector('[data-close-dialog]');
      if (closeButton) {
        closeButton.click();
      }
    }
  };

  containerElement.addEventListener('keydown', handleKeyDown);
  firstElement?.focus();

  return () => {
    containerElement.removeEventListener('keydown', handleKeyDown);
  };
};

/**
 * Generiert eine eindeutige ID für ARIA-Verknüpfungen
 */
let idCounter = 0;
export const generateAriaId = (prefix = 'aria') => {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
};

/**
 * ARIA-Label für dynamische Inhalte
 */
export const getStatusLabel = (status) => {
  const labels = {
    'pending': 'Ausstehend',
    'assigned': 'Zugewiesen',
    'on_site': 'Vor Ort',
    'towed': 'Abgeschleppt',
    'in_yard': 'Im Hof',
    'released': 'Freigegeben',
    'empty_trip': 'Leerfahrt'
  };
  return labels[status] || status;
};

/**
 * Hilfsfunktion für Formular-Fehlermeldungen
 */
export const getFormErrorProps = (fieldName, error) => {
  if (!error) return {};
  
  const errorId = `${fieldName}-error`;
  return {
    'aria-invalid': true,
    'aria-describedby': errorId,
    errorId
  };
};

/**
 * Hilfsfunktion für Pflichtfelder
 */
export const getRequiredFieldProps = (fieldName, label) => ({
  'aria-required': true,
  'aria-label': `${label} (Pflichtfeld)`,
});

/**
 * Tastaturnavigation für Listen/Tabellen
 */
export const handleListKeyDown = (e, items, currentIndex, onSelect) => {
  let newIndex = currentIndex;
  
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      newIndex = Math.min(currentIndex + 1, items.length - 1);
      break;
    case 'ArrowUp':
      e.preventDefault();
      newIndex = Math.max(currentIndex - 1, 0);
      break;
    case 'Home':
      e.preventDefault();
      newIndex = 0;
      break;
    case 'End':
      e.preventDefault();
      newIndex = items.length - 1;
      break;
    case 'Enter':
    case ' ':
      e.preventDefault();
      onSelect?.(items[currentIndex], currentIndex);
      return;
    default:
      return;
  }
  
  if (newIndex !== currentIndex) {
    onSelect?.(items[newIndex], newIndex, 'navigate');
  }
};
