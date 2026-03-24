import React from 'react';
import { Car, ArrowLeft, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useNavigate } from 'react-router-dom';
import { SkipLink } from '../components/accessibility';

/**
 * Erklärung zur Barrierefreiheit (BITV 2.0 / EU-Richtlinie 2016/2102)
 * 
 * Pflichtseite für öffentliche Stellen gemäß § 12b BGG
 */
const BarrierefreiheitPage = () => {
  const navigate = useNavigate();
  const currentDate = new Date().toLocaleDateString('de-DE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="min-h-screen bg-slate-50">
      <SkipLink targetId="main-content" label="Zum Hauptinhalt springen" />
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200" role="banner">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <a href="/" className="flex items-center gap-2" aria-label="Wer Hat Mein Auto Abgeschleppt? - Zur Startseite">
              <Car className="h-8 w-8 text-slate-900" aria-hidden="true" />
              <span className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Wer Hat Mein Auto Abgeschleppt?
              </span>
            </a>
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
              className="flex items-center gap-2"
              aria-label="Zurück zur vorherigen Seite"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Zurück
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main id="main-content" tabIndex={-1} className="max-w-4xl mx-auto px-4 py-12" role="main">
        <h1 className="text-3xl font-bold text-slate-900 mb-8" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Erklärung zur Barrierefreiheit
        </h1>

        <div className="prose prose-slate max-w-none space-y-8">
          {/* Einleitung */}
          <section aria-labelledby="intro-heading">
            <p className="text-lg text-slate-600">
              Diese Erklärung zur Barrierefreiheit gilt für die Webanwendung <strong>Wer Hat Mein Auto Abgeschleppt?</strong> 
              (erreichbar unter der aktuellen Domain). Die Betreiber sind bestrebt, die Webanwendung im 
              Einklang mit den nationalen Rechtsvorschriften zur Umsetzung der EU-Richtlinie 2016/2102 
              barrierefrei zugänglich zu machen.
            </p>
          </section>

          {/* Stand der Vereinbarkeit */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" id="conformity-heading">
                <CheckCircle className="h-5 w-5 text-green-600" aria-hidden="true" />
                Stand der Vereinbarkeit mit den Anforderungen
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Diese Webanwendung ist <strong>weitgehend vereinbar</strong> mit der 
                Barrierefreie-Informationstechnik-Verordnung (BITV 2.0) und den 
                Web Content Accessibility Guidelines (WCAG) 2.1 Level AA.
              </p>
              
              <h3 className="font-semibold text-slate-900 mb-2">Umgesetzte Maßnahmen:</h3>
              <ul className="list-disc pl-6 space-y-2 text-slate-600">
                <li>Skip-Links zum Überspringen von Navigationselementen</li>
                <li>Semantische HTML-Strukturen (Landmarks, Überschriften-Hierarchie)</li>
                <li>ARIA-Labels für alle interaktiven Elemente</li>
                <li>Tastaturnavigation für alle Funktionen</li>
                <li>Sichtbare Fokus-Indikatoren</li>
                <li>Live-Regionen für dynamische Inhaltsänderungen</li>
                <li>Unterstützung für reduzierte Bewegung (prefers-reduced-motion)</li>
                <li>Unterstützung für erhöhten Kontrast (prefers-contrast)</li>
                <li>Mindestgröße von 44×44 Pixel für Touchziele</li>
                <li>Alternative Texte für informative Grafiken</li>
              </ul>
            </CardContent>
          </Card>

          {/* Nicht barrierefreie Inhalte */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" id="limitations-heading">
                <AlertTriangle className="h-5 w-5 text-amber-600" aria-hidden="true" />
                Nicht barrierefreie Inhalte
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Die nachfolgend aufgeführten Inhalte sind aus den folgenden Gründen 
                nicht vollständig barrierefrei:
              </p>
              
              <h3 className="font-semibold text-slate-900 mb-2">Unvereinbarkeit mit BITV 2.0:</h3>
              <ul className="list-disc pl-6 space-y-2 text-slate-600">
                <li>
                  <strong>Kartenansichten:</strong> Die interaktiven Karten (Leaflet/OpenStreetMap) 
                  sind nur eingeschränkt per Tastatur bedienbar. Alternative: Adressinformationen 
                  werden zusätzlich als Text bereitgestellt.
                </li>
                <li>
                  <strong>PDF-Dokumente:</strong> Automatisch generierte Rechnungen und Berichte 
                  sind möglicherweise nicht vollständig barrierefrei. Bei Bedarf können diese 
                  Informationen in alternativer Form angefordert werden.
                </li>
              </ul>
            </CardContent>
          </Card>

          {/* Erstellung dieser Erklärung */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" id="creation-heading">
                <Info className="h-5 w-5 text-blue-600" aria-hidden="true" />
                Erstellung dieser Erklärung
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Diese Erklärung wurde am <strong>{currentDate}</strong> erstellt.
              </p>
              <p className="mb-4">
                Die Einschätzung basiert auf einer <strong>Selbstbewertung</strong> durch 
                den Betreiber unter Verwendung automatisierter Tests und manueller Prüfungen.
              </p>
              <p>
                <strong>Verwendete Prüfmethoden:</strong>
              </p>
              <ul className="list-disc pl-6 space-y-1 text-slate-600 mt-2">
                <li>Tastaturnavigationstest</li>
                <li>Screenreader-Test (NVDA, VoiceOver)</li>
                <li>Kontrastprüfung</li>
                <li>Validierung der HTML-Semantik</li>
                <li>ARIA-Attribut-Prüfung</li>
              </ul>
            </CardContent>
          </Card>

          {/* Feedback und Kontakt */}
          <Card className="border-orange-200 bg-orange-50">
            <CardHeader>
              <CardTitle id="feedback-heading">Feedback und Kontakt</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Wenn Sie Barrieren auf dieser Webanwendung feststellen oder Informationen 
                in einem barrierefreien Format benötigen, kontaktieren Sie uns bitte:
              </p>
              <div className="bg-white p-4 rounded-lg">
                <p><strong>E-Mail:</strong> <a href="mailto:barrierefreiheit@abschleppportal.de" className="text-orange-600 underline">barrierefreiheit@abschleppportal.de</a></p>
                <p className="mt-2"><strong>Anschrift:</strong> [Betreiberadresse einfügen]</p>
              </div>
              <p className="mt-4 text-sm text-slate-600">
                Wir werden versuchen, die mitgeteilten Barrieren zu beseitigen bzw. 
                Ihnen die benötigten Informationen in einer barrierefreien Form zur 
                Verfügung zu stellen.
              </p>
            </CardContent>
          </Card>

          {/* Durchsetzungsverfahren */}
          <Card>
            <CardHeader>
              <CardTitle id="enforcement-heading">Durchsetzungsverfahren</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">
                Wenn auch nach Ihrem Feedback an den oben genannten Kontakt keine 
                zufriedenstellende Lösung gefunden wird, können Sie sich an die 
                zuständige Durchsetzungsstelle wenden:
              </p>
              <div className="bg-slate-100 p-4 rounded-lg text-sm">
                <p><strong>Schlichtungsstelle nach § 16 BGG</strong></p>
                <p>beim Beauftragten der Bundesregierung für die Belange von Menschen mit Behinderungen</p>
                <p className="mt-2">Mauerstraße 53, 10117 Berlin</p>
                <p>Telefon: <a href="tel:+4930185272805" className="text-orange-600 underline">+49 30 18527-2805</a></p>
                <p>E-Mail: <a href="mailto:info@schlichtungsstelle-bgg.de" className="text-orange-600 underline">info@schlichtungsstelle-bgg.de</a></p>
                <p>Website: <a href="https://www.schlichtungsstelle-bgg.de" target="_blank" rel="noopener noreferrer" className="text-orange-600 underline">www.schlichtungsstelle-bgg.de</a></p>
              </div>
            </CardContent>
          </Card>

          {/* Technische Informationen */}
          <section aria-labelledby="tech-heading">
            <h2 id="tech-heading" className="text-xl font-semibold text-slate-900 mb-4">
              Technische Informationen zur Barrierefreiheit
            </h2>
            <p className="text-slate-600">
              Diese Webanwendung wurde unter Verwendung folgender Technologien entwickelt, 
              deren Barrierefreiheit abhängig ist:
            </p>
            <ul className="list-disc pl-6 space-y-1 text-slate-600 mt-2">
              <li>HTML5</li>
              <li>WAI-ARIA 1.1</li>
              <li>CSS / Tailwind CSS</li>
              <li>JavaScript / React</li>
            </ul>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-8 px-4 mt-12" role="contentinfo">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-slate-400 text-sm">
            © {new Date().getFullYear()} Wer Hat Mein Auto Abgeschleppt? Alle Rechte vorbehalten.
          </p>
          <nav className="mt-4 flex justify-center gap-6" aria-label="Rechtliche Hinweise">
            <a href="/datenschutz" className="text-slate-400 hover:text-white text-sm underline">Datenschutz</a>
            <a href="/impressum" className="text-slate-400 hover:text-white text-sm underline">Impressum</a>
            <a href="/barrierefreiheit" className="text-slate-400 hover:text-white text-sm underline" aria-current="page">Barrierefreiheit</a>
          </nav>
        </div>
      </footer>
    </div>
  );
};

export default BarrierefreiheitPage;
