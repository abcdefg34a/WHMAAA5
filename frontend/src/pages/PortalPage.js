import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Car, Shield, Truck, UserPlus, LogIn, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

export const PortalPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Car className="h-8 w-8 text-slate-900" />
              <span className="font-bold text-xl text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                AbschleppPortal
              </span>
              <span className="ml-2 px-2 py-1 bg-slate-200 text-slate-600 text-xs rounded">
                Interner Bereich
              </span>
            </div>
            <Button
              variant="ghost"
              onClick={() => navigate('/')}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Zur Startseite
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Internes Portal
          </h1>
          <p className="text-slate-600">
            Zugang für Behörden und Abschleppdienste
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Login Card */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <LogIn className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <CardTitle>Anmelden</CardTitle>
                  <CardDescription>Bereits registriert?</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-slate-600 mb-4">
                Melden Sie sich mit Ihren bestehenden Zugangsdaten an.
              </p>
              <Button 
                className="w-full bg-blue-600 hover:bg-blue-700"
                onClick={() => navigate('/login')}
              >
                <LogIn className="h-4 w-4 mr-2" />
                Zum Login
              </Button>
            </CardContent>
          </Card>

          {/* Register Card */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-3 bg-green-100 rounded-lg">
                  <UserPlus className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <CardTitle>Registrieren</CardTitle>
                  <CardDescription>Neu hier?</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-slate-600 mb-4">
                Erstellen Sie einen neuen Account für Ihre Organisation.
              </p>
              <Button 
                className="w-full bg-green-600 hover:bg-green-700"
                onClick={() => navigate('/register')}
              >
                <UserPlus className="h-4 w-4 mr-2" />
                Registrieren
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Role Info */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card className="bg-slate-50 border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-amber-100 rounded">
                  <Shield className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Behörden</h3>
                  <p className="text-sm text-slate-600">
                    Ordnungsämter, Polizei und andere Behörden können hier Abschleppaufträge erstellen und verwalten.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-50 border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-orange-100 rounded">
                  <Truck className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">Abschleppdienste</h3>
                  <p className="text-sm text-slate-600">
                    Abschleppunternehmen können hier Aufträge annehmen, Status aktualisieren und Fahrzeuge verwalten.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Info Note */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg text-center">
          <p className="text-sm text-blue-800">
            <strong>Hinweis:</strong> Neue Registrierungen müssen von einem Administrator freigegeben werden, 
            bevor der Zugang aktiviert wird.
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-sm text-slate-500">
        <p>© {new Date().getFullYear()} AbschleppPortal. Alle Rechte vorbehalten.</p>
      </footer>
    </div>
  );
};

export default PortalPage;
