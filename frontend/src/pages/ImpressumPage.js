import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Building2 } from 'lucide-react';
import { Button } from '../components/ui/button';

export const ImpressumPage = () => {
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
            <Building2 className="h-6 w-6 text-orange-500" />
            <h1 className="text-xl font-bold">Impressum</h1>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm p-8 prose prose-slate max-w-none">
          <h1>Impressum</h1>

          <h2>Angaben gemäß § 5 TMG</h2>
          <p>
            <strong>[Firmenname eintragen]</strong><br />
            [Straße und Hausnummer]<br />
            [PLZ Ort]<br />
            Deutschland
          </p>

          <h2>Vertreten durch</h2>
          <p>[Name des Vertretungsberechtigten]</p>

          <h2>Kontakt</h2>
          <p>
            Telefon: [Telefonnummer]<br />
            E-Mail: [E-Mail-Adresse]
          </p>

          <h2>Registereintrag</h2>
          <p>
            Eintragung im Handelsregister.<br />
            Registergericht: [Amtsgericht]<br />
            Registernummer: [HRB-Nummer]
          </p>

          <h2>Umsatzsteuer-ID</h2>
          <p>
            Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz:<br />
            [USt-IdNr.]
          </p>

          <h2>Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h2>
          <p>
            [Name]<br />
            [Adresse]
          </p>

          <h2>EU-Streitschlichtung</h2>
          <p>
            Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit: 
            <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noopener noreferrer">
              https://ec.europa.eu/consumers/odr/
            </a>
          </p>
          <p>Unsere E-Mail-Adresse finden Sie oben im Impressum.</p>

          <h2>Verbraucherstreitbeilegung / Universalschlichtungsstelle</h2>
          <p>
            Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren 
            vor einer Verbraucherschlichtungsstelle teilzunehmen.
          </p>

          <h2>Haftung für Inhalte</h2>
          <p>
            Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene Inhalte auf diesen 
            Seiten nach den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind 
            wir als Diensteanbieter jedoch nicht verpflichtet, übermittelte oder gespeicherte 
            fremde Informationen zu überwachen oder nach Umständen zu forschen, die auf eine 
            rechtswidrige Tätigkeit hinweisen.
          </p>
          <p>
            Verpflichtungen zur Entfernung oder Sperrung der Nutzung von Informationen nach 
            den allgemeinen Gesetzen bleiben hiervon unberührt. Eine diesbezügliche Haftung 
            ist jedoch erst ab dem Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung 
            möglich. Bei Bekanntwerden von entsprechenden Rechtsverletzungen werden wir diese 
            Inhalte umgehend entfernen.
          </p>

          <h2>Haftung für Links</h2>
          <p>
            Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir 
            keinen Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine 
            Gewähr übernehmen. Für die Inhalte der verlinkten Seiten ist stets der jeweilige 
            Anbieter oder Betreiber der Seiten verantwortlich.
          </p>

          <h2>Urheberrecht</h2>
          <p>
            Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten 
            unterliegen dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, 
            Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes 
            bedürfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers. 
            Downloads und Kopien dieser Seite sind nur für den privaten, nicht kommerziellen 
            Gebrauch gestattet.
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

export default ImpressumPage;
