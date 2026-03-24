import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Search, Car, MapPin, Clock, Phone, Building2, ChevronRight, Shield, Truck, Users, Euro, Calendar, FileText } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { SkipLink } from '../components/accessibility';

// Fix Leaflet default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const LandingPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    setError('');
    setSearchResult(null);

    try {
      const response = await axios.get(`${API}/search/vehicle?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchResult(response.data);
    } catch (err) {
      setError('Fehler bei der Suche. Bitte versuchen Sie es erneut.');
    } finally {
      setSearching(false);
    }
  };

  const getStatusText = (status) => {
    const statusMap = {
      'towed': 'Abgeschleppt',
      'in_yard': 'Im Hof'
    };
    return statusMap[status] || status;
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Skip-Link für Barrierefreiheit (BITV 2.0) */}
      <SkipLink targetId="main-content" label="Zum Hauptinhalt springen" />
      
      {/* Header */}
      <header className="bg-white border-b border-slate-200" role="banner">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <a href="/" className="flex items-center gap-2" aria-label="Wer Hat Mein Auto Abgeschleppt? - Zur Startseite">
              <Car className="h-8 w-8 text-slate-900" aria-hidden="true" />
              <span className="font-bold text-xl text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Wer Hat Mein Auto Abgeschleppt?
              </span>
            </a>
            {/* Login button removed - access only via /portal */}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section
        id="main-content"
        tabIndex={-1}
        className="hero-section relative py-24 md:py-32"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=1600&q=80)',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
        role="region"
        aria-label="Fahrzeugsuche"
      >
        <div className="hero-overlay absolute inset-0" aria-hidden="true"></div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 text-center">
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-black text-white mb-6"
            style={{ fontFamily: 'Chivo, sans-serif' }}
          >
            Wurde Ihr Fahrzeug abgeschleppt?
          </h1>
          <p className="text-lg md:text-xl text-slate-200 mb-10">
            Finden Sie Ihr Fahrzeug in Sekunden. Geben Sie Ihr Kennzeichen oder Ihre FIN ein.
          </p>

          {/* Search Form - German License Plate Format */}
          <form onSubmit={handleSearch} className="max-w-xl mx-auto" role="search" aria-label="Fahrzeugsuche">
            <div className="bg-white rounded-lg p-4 shadow-lg">
              {/* License Plate Visual Format */}
              <div className="flex items-center justify-center mb-3">
                <div className="flex items-center bg-white border-2 border-slate-300 rounded-md overflow-hidden">
                  {/* EU Field */}
                  <div className="bg-blue-700 text-white px-2 py-3 flex flex-col items-center" aria-hidden="true">
                    <div className="text-xs">★★★</div>
                    <div className="font-bold text-sm">D</div>
                  </div>
                  {/* Input Field */}
                  <label htmlFor="vehicle-search" className="sr-only">Kennzeichen oder FIN eingeben</label>
                  <input
                    id="vehicle-search"
                    data-testid="vehicle-search-input"
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                    placeholder="B AB 1234 oder FIN..."
                    maxLength={17}
                    className="text-xl md:text-2xl font-bold text-center py-3 px-4 w-full border-0 outline-none tracking-wider"
                    style={{ fontFamily: 'monospace' }}
                    aria-describedby="search-format-hint"
                    autoComplete="off"
                  />
                </div>
              </div>

              {/* Format Examples */}
              <p id="search-format-hint" className="text-xs text-slate-500 text-center mb-3">
                Beispiele: <span className="font-mono bg-slate-100 px-1 rounded">B AB 1234</span>, <span className="font-mono bg-slate-100 px-1 rounded">HH XY 999E</span> oder 17-stellige FIN
              </p>

              {/* Search Button */}
              <button
                data-testid="vehicle-search-btn"
                type="submit"
                disabled={searching}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors touch-target"
                aria-busy={searching}
              >
                {searching ? (
                  <>
                    <div className="loading-spinner" aria-hidden="true"></div>
                    <span>Suche läuft...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-5 w-5" aria-hidden="true" />
                    <span>Fahrzeug suchen</span>
                  </>
                )}
              </button>
            </div>

            {/* Pickup Hint */}
            <div className="mt-4 bg-amber-500/90 text-white px-4 py-3 rounded-lg text-sm" role="note" aria-label="Hinweis zur Abholung">
              <p className="font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4" aria-hidden="true" />
                Bei Treffer zur Abholung mitbringen:
              </p>
              <ul className="mt-1 ml-6 list-disc text-amber-100">
                <li>Personalausweis oder Reisepass</li>
                <li>Fahrzeugpapiere (Zulassungsbescheinigung Teil I)</li>
              </ul>
            </div>
          </form>

          {error && (
            <div role="alert" aria-live="assertive" className="mt-4 bg-red-500/20 text-red-200 px-4 py-3 rounded-lg">
              <p className="font-medium">{error}</p>
            </div>
          )}
        </div>
      </section>

      {/* Search Result */}
      {searchResult && (
        <section className="py-12 px-4" aria-label="Suchergebnis" role="region" aria-live="polite">
          <div className="max-w-4xl mx-auto">
            {searchResult.found ? (
              <Card data-testid="search-result-found" className="border-2 border-orange-500" role="article" aria-label="Fahrzeug gefunden">
                <CardContent className="p-6 md:p-8">
                  <div className="flex items-start gap-4 mb-6">
                    <div className="bg-orange-100 p-3 rounded-lg" aria-hidden="true">
                      <Car className="h-8 w-8 text-orange-600" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        Fahrzeug gefunden!
                      </h2>
                      <p className="text-slate-600">Auftragsnummer: <span className="font-mono">{searchResult.job_number}</span></p>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-slate-100 p-2 rounded" aria-hidden="true">
                          <Car className="h-5 w-5 text-slate-600" />
                        </div>
                        <div>
                          <p className="text-sm text-slate-500">Kennzeichen</p>
                          <p className="font-bold text-lg">{searchResult.license_plate}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium status-${searchResult.status}`} role="status">
                          <span className="sr-only">Status: </span>{getStatusText(searchResult.status)}
                        </div>
                      </div>

                      {searchResult.towed_at && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded" aria-hidden="true">
                            <Clock className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Abgeschleppt am</p>
                            <p className="font-medium">
                              <time dateTime={searchResult.towed_at}>{new Date(searchResult.towed_at).toLocaleString('de-DE')}</time>
                            </p>
                          </div>
                        </div>
                      )}

                      {searchResult.tow_reason && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <FileText className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Grund</p>
                            <p className="font-medium">{searchResult.tow_reason}</p>
                          </div>
                        </div>
                      )}

                      {searchResult.location_address && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <MapPin className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Abgeschleppt von</p>
                            <p className="font-medium">{searchResult.location_address}</p>
                          </div>
                        </div>
                      )}

                      {searchResult.created_by_authority && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Building2 className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Auftrag von</p>
                            <p className="font-medium">{searchResult.created_by_authority}</p>
                          </div>
                        </div>
                      )}

                      {searchResult.days_in_yard > 0 && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Calendar className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Standzeit</p>
                            <p className="font-medium">{searchResult.days_in_yard} Tag(e)</p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-4">
                      {searchResult.company_name && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Building2 className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Abschleppdienst</p>
                            <p className="font-medium">{searchResult.company_name}</p>
                          </div>
                        </div>
                      )}

                      {searchResult.phone && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Phone className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Telefon</p>
                            <p className="font-medium">{searchResult.phone}</p>
                          </div>
                        </div>
                      )}

                      {searchResult.opening_hours && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Clock className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Öffnungszeiten</p>
                            <p className="font-medium">{searchResult.opening_hours}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Cost Calculation */}
                  {searchResult.total_cost !== null && searchResult.total_cost > 0 && (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <Euro className="h-5 w-5 text-orange-600" />
                        <h3 className="font-bold text-lg text-orange-900">Geschätzte Kosten (Stand heute)</h3>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between py-1 border-b border-orange-200">
                          <span className="text-orange-700">Anfahrt/Abschleppen</span>
                          <span className="font-semibold text-orange-900">{searchResult.tow_cost?.toFixed(2)} €</span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-orange-200">
                          <span className="text-orange-700">Standkosten ({searchResult.days_in_yard} Tag(e) × {searchResult.daily_cost?.toFixed(2)} €)</span>
                          <span className="font-semibold text-orange-900">{(searchResult.daily_cost * searchResult.days_in_yard).toFixed(2)} €</span>
                        </div>
                        {searchResult.processing_fee > 0 && (
                          <div className="flex justify-between py-1 border-b border-orange-200">
                            <span className="text-orange-700">Bearbeitungsgebühr</span>
                            <span className="font-semibold text-orange-900">{searchResult.processing_fee?.toFixed(2)} €</span>
                          </div>
                        )}
                        {searchResult.heavy_vehicle_surcharge > 0 && (
                          <div className="flex justify-between py-1 border-b border-orange-200">
                            <span className="text-orange-700">Schwerlastzuschlag (ab 3,5t)</span>
                            <span className="font-semibold text-orange-900">{searchResult.heavy_vehicle_surcharge?.toFixed(2)} €</span>
                          </div>
                        )}
                        {searchResult.empty_trip_fee > 0 && (
                          <div className="flex justify-between py-1 border-b border-orange-200">
                            <span className="text-orange-700">Leerfahrt</span>
                            <span className="font-semibold text-orange-900">{searchResult.empty_trip_fee?.toFixed(2)} €</span>
                          </div>
                        )}
                        {searchResult.night_surcharge > 0 && (
                          <div className="flex justify-between py-1 border-b border-orange-200">
                            <span className="text-orange-700">Nachtzuschlag</span>
                            <span className="font-semibold text-orange-900">{searchResult.night_surcharge?.toFixed(2)} €</span>
                          </div>
                        )}
                        {searchResult.weekend_surcharge > 0 && (
                          <div className="flex justify-between py-1 border-b border-orange-200">
                            <span className="text-orange-700">Wochenendzuschlag</span>
                            <span className="font-semibold text-orange-900">{searchResult.weekend_surcharge?.toFixed(2)} €</span>
                          </div>
                        )}
                        <div className="flex justify-between py-2 mt-2 bg-orange-100 rounded-lg px-3">
                          <span className="font-bold text-orange-900">Gesamtbetrag</span>
                          <span className="font-black text-xl text-orange-900">{searchResult.total_cost?.toFixed(2)} €</span>
                        </div>
                      </div>
                      <p className="text-xs text-orange-600 mt-3">
                        * Die Kosten erhöhen sich täglich um {searchResult.daily_cost?.toFixed(2)} € Standgebühr
                      </p>
                    </div>
                  )}

                  {searchResult.yard_address && (
                    <div className="border-t pt-6">
                      <div className="flex items-center gap-3 mb-4">
                        <MapPin className="h-5 w-5 text-slate-600" />
                        <div>
                          <p className="text-sm text-slate-500">Standort des Abschlepphofs</p>
                          <p className="font-medium">{searchResult.yard_address}</p>
                        </div>
                      </div>

                      {/* Interaktive Karte - zeigt Hof-Standort */}
                      {searchResult.yard_lat && searchResult.yard_lng && (
                        <div className="rounded-lg overflow-hidden border border-slate-200 mb-4" style={{ height: '250px' }}>
                          <MapContainer
                            center={[searchResult.yard_lat, searchResult.yard_lng]}
                            zoom={15}
                            style={{ height: '100%', width: '100%' }}
                            scrollWheelZoom={false}
                          >
                            <TileLayer
                              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            />
                            <Marker position={[searchResult.yard_lat, searchResult.yard_lng]}>
                              <Popup>
                                <strong>{searchResult.company_name}</strong><br />
                                {searchResult.yard_address}
                              </Popup>
                            </Marker>
                          </MapContainer>
                        </div>
                      )}

                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(searchResult.yard_address)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-md hover:bg-slate-800 transition-colors font-medium"
                      >
                        <MapPin className="h-5 w-5" />
                        Route in Google Maps öffnen
                      </a>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card data-testid="search-result-not-found" className="bg-slate-100 border-slate-200">
                <CardContent className="p-8 text-center">
                  <Car className="h-16 w-16 text-slate-400 mx-auto mb-4" />
                  <h2 className="text-xl font-bold text-slate-700 mb-2">
                    Kein Fahrzeug gefunden
                  </h2>
                  <p className="text-slate-500">
                    Mit dieser Eingabe wurde kein abgeschlepptes Fahrzeug gefunden.
                    Bitte überprüfen Sie Ihre Eingabe.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* How it Works */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-slate-900 mb-12" style={{ fontFamily: 'Chivo, sans-serif' }}>
            So funktioniert es
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-slate-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="h-8 w-8 text-slate-700" />
              </div>
              <h3 className="font-bold text-lg mb-2">1. Suchen</h3>
              <p className="text-slate-600">
                Geben Sie Ihr Kennzeichen oder Ihre FIN in das Suchfeld ein.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-slate-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Euro className="h-8 w-8 text-slate-700" />
              </div>
              <h3 className="font-bold text-lg mb-2">2. Kosten einsehen</h3>
              <p className="text-slate-600">
                Sehen Sie sofort die aktuellen Abschleppkosten inkl. Standgebühren.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-slate-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Car className="h-8 w-8 text-slate-700" />
              </div>
              <h3 className="font-bold text-lg mb-2">3. Abholen</h3>
              <p className="text-slate-600">
                Navigieren Sie direkt zum Abschleppgelände und holen Sie Ihr Fahrzeug ab.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-12 px-4" role="contentinfo">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <Car className="h-8 w-8" aria-hidden="true" />
              <span className="font-bold text-xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Wer Hat Mein Auto Abgeschleppt?
              </span>
            </div>
            <nav className="flex flex-col md:flex-row items-center gap-4 md:gap-8" aria-label="Rechtliche Hinweise">
              <div className="flex gap-6">
                <a
                  href="/datenschutz"
                  className="text-slate-400 hover:text-white text-sm transition-colors underline underline-offset-2"
                >
                  Datenschutz
                </a>
                <a
                  href="/impressum"
                  className="text-slate-400 hover:text-white text-sm transition-colors underline underline-offset-2"
                >
                  Impressum
                </a>
                <a
                  href="/barrierefreiheit"
                  className="text-slate-400 hover:text-white text-sm transition-colors underline underline-offset-2"
                >
                  Barrierefreiheit
                </a>
              </div>
              <p className="text-slate-400 text-sm">
                © {new Date().getFullYear()} Wer Hat Mein Auto Abgeschleppt? Alle Rechte vorbehalten.
              </p>
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
