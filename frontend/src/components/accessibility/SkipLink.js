import React from 'react';

/**
 * Skip-Link Komponente für Barrierefreiheit (BITV 2.0 / WCAG 2.4.1)
 * 
 * Ermöglicht Tastaturnutzern, direkt zum Hauptinhalt zu springen
 * und wiederholte Navigationselemente zu überspringen.
 */
export const SkipLink = ({ targetId = "main-content", label = "Zum Hauptinhalt springen" }) => {
  const handleClick = (e) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <a
      href={`#${targetId}`}
      className="skip-link"
      onClick={handleClick}
    >
      {label}
    </a>
  );
};

/**
 * Zusätzliche Navigation-Skip-Links für komplexe Seiten
 */
export const SkipLinks = ({ links }) => {
  return (
    <nav aria-label="Schnellnavigation" className="sr-only focus-within:not-sr-only">
      <ul className="flex gap-2 p-2 bg-slate-900 text-white">
        {links.map((link, index) => (
          <li key={index}>
            <a
              href={`#${link.id}`}
              className="skip-link"
              onClick={(e) => {
                e.preventDefault();
                const target = document.getElementById(link.id);
                if (target) {
                  target.focus();
                  target.scrollIntoView({ behavior: 'smooth' });
                }
              }}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default SkipLink;
