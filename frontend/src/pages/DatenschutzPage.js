import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield } from 'lucide-react';
import { Button } from '../components/ui/button';

export const DatenschutzPage = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Zurück
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-orange-500" />
            <h1 className="text-xl font-bold">Datenschutzerklärung</h1>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm p-8 prose prose-slate max-w-none">
          <h1>Datenschutzerklärung</h1>
          <p><strong>Stand:</strong> {new Date().toLocaleDateString('de-DE')}</p>

          <h2>1. Verantwortlicher</h2>
          <p>
            Verantwortlich für die Datenverarbeitung auf dieser Website ist:<br />
            <em>[Ihr Unternehmen eintragen]</em><br />
            <em>[Adresse eintragen]</em><br />
            E-Mail: <em>[E-Mail eintragen]</em>
          </p>

          <h2>2. Erhebung und Speicherung personenbezogener Daten</h2>
          <h3>2.1 Bei Registrierung</h3>
          <p>Bei der Registrierung erheben wir folgende Daten:</p>
          <ul>
            <li>E-Mail-Adresse</li>
            <li>Name / Ansprechpartner</li>
            <li>Bei Behörden: Behördenname, Abteilung</li>
            <li>Bei Abschleppdiensten: Firmenname, Adresse, Telefon, Öffnungszeiten, Gewerbenachweis</li>
          </ul>

          <h3>2.2 Bei Nutzung der Plattform</h3>
          <p>Bei der Erfassung von Abschleppvorgängen werden gespeichert:</p>
          <ul>
            <li>Fahrzeugkennzeichen und FIN</li>
            <li>Standort des Fahrzeugs (Adresse und GPS-Koordinaten)</li>
            <li>Fotos des Fahrzeugs</li>
            <li>Abschleppgrund</li>
            <li>Zeitstempel aller Statusänderungen</li>
            <li>Bei Abholung: Name und Adresse des Halters</li>
          </ul>

          <h2>3. Zweck der Datenverarbeitung</h2>
          <p>Die Daten werden verarbeitet für:</p>
          <ul>
            <li>Verwaltung und Dokumentation von Abschleppvorgängen</li>
            <li>Kommunikation zwischen Behörden und Abschleppdiensten</li>
            <li>Ermöglichung der Fahrzeugsuche für Halter</li>
            <li>Erstellung von Protokollen und Rechnungen</li>
            <li>Statistische Auswertungen</li>
          </ul>

          <h2>4. Rechtsgrundlage</h2>
          <p>
            Die Verarbeitung erfolgt auf Grundlage von Art. 6 Abs. 1 lit. b DSGVO 
            (Vertragserfüllung) sowie Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse 
            an der ordnungsgemäßen Durchführung von Abschleppvorgängen).
          </p>

          <h2>5. Speicherdauer</h2>
          <p>
            Personenbezogene Daten werden gelöscht, sobald der Zweck der Speicherung entfällt. 
            Für Abschleppvorgänge gilt eine Aufbewahrungsfrist von [X] Jahren gemäß den 
            gesetzlichen Anforderungen.
          </p>

          <h2>6. Ihre Rechte</h2>
          <p>Sie haben das Recht auf:</p>
          <ul>
            <li><strong>Auskunft</strong> über Ihre gespeicherten Daten (Art. 15 DSGVO)</li>
            <li><strong>Berichtigung</strong> unrichtiger Daten (Art. 16 DSGVO)</li>
            <li><strong>Löschung</strong> Ihrer Daten (Art. 17 DSGVO)</li>
            <li><strong>Einschränkung der Verarbeitung</strong> (Art. 18 DSGVO)</li>
            <li><strong>Datenübertragbarkeit</strong> (Art. 20 DSGVO)</li>
            <li><strong>Widerspruch</strong> gegen die Verarbeitung (Art. 21 DSGVO)</li>
          </ul>

          <h2>7. Datensicherheit</h2>
          <p>
            Wir setzen technische und organisatorische Sicherheitsmaßnahmen ein, 
            um Ihre Daten gegen Manipulation, Verlust oder unberechtigten Zugriff zu schützen:
          </p>
          <ul>
            <li>Verschlüsselte Datenübertragung (HTTPS/TLS)</li>
            <li>Passwortschutz mit Mindestanforderungen</li>
            <li>Regelmäßige Sicherheitsupdates</li>
            <li>Zugriffsbeschränkungen nach dem Prinzip der minimalen Rechte</li>
            <li>Protokollierung von Zugriffen (Audit-Log)</li>
          </ul>

          <h2>8. Kontakt bei Datenschutzfragen</h2>
          <p>
            Bei Fragen zum Datenschutz wenden Sie sich bitte an:<br />
            E-Mail: <em>[Datenschutz-E-Mail eintragen]</em>
          </p>

          <h2>9. Beschwerderecht</h2>
          <p>
            Sie haben das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu beschweren, 
            wenn Sie der Ansicht sind, dass die Verarbeitung Ihrer personenbezogenen Daten 
            gegen die DSGVO verstößt.
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t py-6 mt-8">
        <div className="max-w-4xl mx-auto px-4 text-center text-sm text-slate-500">
          <div className="flex justify-center gap-4">
            <Link to="/impressum" className="hover:text-slate-700">Impressum</Link>
            <span>|</span>
            <Link to="/datenschutz" className="hover:text-slate-700">Datenschutz</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default DatenschutzPage;
