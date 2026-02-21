import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Search, Car, MapPin, Clock, Phone, Building2, ChevronRight, Shield, Truck, Users, Euro, Calendar } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

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
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Car className="h-8 w-8 text-slate-900" />
              <span className="font-bold text-xl text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                AbschleppPortal
              </span>
            </div>
            <Button
              data-testid="login-btn"
              onClick={() => navigate('/login')}
              className="bg-slate-900 text-white hover:bg-slate-800"
            >
              Anmelden
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section 
        className="hero-section relative py-24 md:py-32"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=1600&q=80)',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="hero-overlay absolute inset-0"></div>
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

          {/* Search Form */}
          <form onSubmit={handleSearch} className="max-w-xl mx-auto">
            <div className="relative">
              <input
                data-testid="vehicle-search-input"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                placeholder="Kennzeichen oder FIN eingeben"
                className="license-plate-input w-full pr-16"
              />
              <button
                data-testid="vehicle-search-btn"
                type="submit"
                disabled={searching}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-orange-500 hover:bg-orange-600 text-white p-3 rounded transition-colors"
              >
                {searching ? (
                  <div className="loading-spinner"></div>
                ) : (
                  <Search className="h-6 w-6" />
                )}
              </button>
            </div>
          </form>

          {error && (
            <p className="mt-4 text-red-400">{error}</p>
          )}
        </div>
      </section>

      {/* Search Result */}
      {searchResult && (
        <section className="py-12 px-4">
          <div className="max-w-4xl mx-auto">
            {searchResult.found ? (
              <Card data-testid="search-result-found" className="border-2 border-orange-500">
                <CardContent className="p-6 md:p-8">
                  <div className="flex items-start gap-4 mb-6">
                    <div className="bg-orange-100 p-3 rounded-lg">
                      <Car className="h-8 w-8 text-orange-600" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                        Fahrzeug gefunden!
                      </h2>
                      <p className="text-slate-600">Auftragsnummer: {searchResult.job_number}</p>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="bg-slate-100 p-2 rounded">
                          <Car className="h-5 w-5 text-slate-600" />
                        </div>
                        <div>
                          <p className="text-sm text-slate-500">Kennzeichen</p>
                          <p className="font-bold text-lg">{searchResult.license_plate}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium status-${searchResult.status}`}>
                          {getStatusText(searchResult.status)}
                        </div>
                      </div>

                      {searchResult.towed_at && (
                        <div className="flex items-center gap-3">
                          <div className="bg-slate-100 p-2 rounded">
                            <Clock className="h-5 w-5 text-slate-600" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-500">Abgeschleppt am</p>
                            <p className="font-medium">
                              {new Date(searchResult.towed_at).toLocaleString('de-DE')}
                            </p>
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
                      <div className="grid sm:grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-orange-700">Anfahrtskosten</p>
                          <p className="font-bold text-lg text-orange-900">{searchResult.tow_cost?.toFixed(2)} €</p>
                        </div>
                        <div>
                          <p className="text-orange-700">Standkosten ({searchResult.days_in_yard} Tag(e) × {searchResult.daily_cost?.toFixed(2)} €)</p>
                          <p className="font-bold text-lg text-orange-900">{(searchResult.daily_cost * searchResult.days_in_yard).toFixed(2)} €</p>
                        </div>
                        <div className="bg-orange-100 rounded-lg p-3">
                          <p className="text-orange-700">Gesamt</p>
                          <p className="font-black text-2xl text-orange-900">{searchResult.total_cost?.toFixed(2)} €</p>
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
                          <p className="text-sm text-slate-500">Standort des Fahrzeugs</p>
                          <p className="font-medium">{searchResult.yard_address}</p>
                        </div>
                      </div>

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

      {/* For Professionals */}
      <section className="py-16 px-4 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-slate-900 mb-4" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Für Behörden & Abschleppdienste
          </h2>
          <p className="text-center text-slate-600 mb-12 max-w-2xl mx-auto">
            Digitalisieren Sie Ihren Abschleppprozess mit unserer professionellen Plattform.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="card-hover">
              <CardContent className="p-6">
                <Shield className="h-10 w-10 text-orange-500 mb-4" />
                <h3 className="font-bold text-lg mb-2">Behörden</h3>
                <p className="text-slate-600 mb-4">
                  Erfassen Sie Fahrzeuge vor Ort mit Fotos, Standort und allen relevanten Daten.
                </p>
                <Button 
                  variant="outline"
                  onClick={() => navigate('/register?role=authority')}
                  className="w-full"
                >
                  Mehr erfahren <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </CardContent>
            </Card>
            <Card className="card-hover">
              <CardContent className="p-6">
                <Truck className="h-10 w-10 text-orange-500 mb-4" />
                <h3 className="font-bold text-lg mb-2">Abschleppdienste</h3>
                <p className="text-slate-600 mb-4">
                  Empfangen Sie Aufträge digital und verwalten Sie Ihren Fuhrpark effizient.
                </p>
                <Button 
                  variant="outline"
                  onClick={() => navigate('/register?role=towing_service')}
                  className="w-full"
                >
                  Registrieren <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </CardContent>
            </Card>
            <Card className="card-hover">
              <CardContent className="p-6">
                <Users className="h-10 w-10 text-orange-500 mb-4" />
                <h3 className="font-bold text-lg mb-2">Transparenz</h3>
                <p className="text-slate-600 mb-4">
                  Bürger können ihr abgeschlepptes Fahrzeug einfach online finden.
                </p>
                <Button 
                  variant="outline"
                  onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  className="w-full"
                >
                  Jetzt suchen <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <Car className="h-8 w-8" />
              <span className="font-bold text-xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
                AbschleppPortal
              </span>
            </div>
            <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8">
              <div className="flex gap-6">
                <a 
                  href="/datenschutz" 
                  className="text-slate-400 hover:text-white text-sm transition-colors"
                >
                  Datenschutz
                </a>
                <a 
                  href="/impressum" 
                  className="text-slate-400 hover:text-white text-sm transition-colors"
                >
                  Impressum
                </a>
              </div>
              <p className="text-slate-400 text-sm">
                © {new Date().getFullYear()} AbschleppPortal. Alle Rechte vorbehalten.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
