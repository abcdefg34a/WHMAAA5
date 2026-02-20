import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Car, Eye, EyeOff, ArrowLeft, Shield, Truck, MapPin } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

export const RegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('role') || 'authority');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Common fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');

  // Authority fields
  const [authorityName, setAuthorityName] = useState('');
  const [department, setDepartment] = useState('');

  // Towing service fields
  const [companyName, setCompanyName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [yardAddress, setYardAddress] = useState('');
  const [yardLat, setYardLat] = useState('');
  const [yardLng, setYardLng] = useState('');
  const [openingHours, setOpeningHours] = useState('');

  useEffect(() => {
    const role = searchParams.get('role');
    if (role && (role === 'authority' || role === 'towing_service')) {
      setActiveTab(role);
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = {
        email,
        password,
        name,
        role: activeTab
      };

      if (activeTab === 'authority') {
        data.authority_name = authorityName;
        data.department = department;
      } else if (activeTab === 'towing_service') {
        data.company_name = companyName;
        data.phone = phone;
        data.address = address;
        data.yard_address = yardAddress;
        data.yard_lat = yardLat ? parseFloat(yardLat) : null;
        data.yard_lng = yardLng ? parseFloat(yardLng) : null;
        data.opening_hours = openingHours;
      }

      const user = await register(data);
      
      if (user.role === 'authority') {
        navigate('/authority');
      } else if (user.role === 'towing_service') {
        navigate('/towing');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registrierung fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setYardLat(position.coords.latitude.toString());
          setYardLng(position.coords.longitude.toString());
        },
        (err) => {
          console.error('Location error:', err);
        }
      );
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{
        background: 'linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%)'
      }}
    >
      <div className="w-full max-w-lg">
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-8"
        >
          <ArrowLeft className="h-4 w-4" />
          Zurück zur Startseite
        </Link>

        <Card className="shadow-xl border-slate-200">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="bg-slate-900 p-3 rounded-xl">
                <Car className="h-8 w-8 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Registrieren
            </CardTitle>
            <CardDescription>
              Erstellen Sie ein neues Konto
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger 
                  data-testid="register-tab-authority"
                  value="authority" 
                  className="flex items-center gap-2"
                >
                  <Shield className="h-4 w-4" />
                  Behörde
                </TabsTrigger>
                <TabsTrigger 
                  data-testid="register-tab-towing"
                  value="towing_service"
                  className="flex items-center gap-2"
                >
                  <Truck className="h-4 w-4" />
                  Abschleppdienst
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div 
                  data-testid="register-error"
                  className="bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm"
                >
                  {error}
                </div>
              )}

              {/* Common Fields */}
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  data-testid="register-name-input"
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ihr Name"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">E-Mail</Label>
                <Input
                  data-testid="register-email-input"
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ihre@email.de"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Passwort</Label>
                <div className="relative">
                  <Input
                    data-testid="register-password-input"
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    minLength={6}
                    className="pr-12"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Authority-specific fields */}
              {activeTab === 'authority' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="authorityName">Behörde / Amt</Label>
                    <Input
                      data-testid="register-authority-name-input"
                      id="authorityName"
                      value={authorityName}
                      onChange={(e) => setAuthorityName(e.target.value)}
                      placeholder="z.B. Ordnungsamt München"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="department">Abteilung</Label>
                    <Input
                      data-testid="register-department-input"
                      id="department"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      placeholder="z.B. Verkehrsüberwachung"
                    />
                  </div>
                </>
              )}

              {/* Towing service-specific fields */}
              {activeTab === 'towing_service' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="companyName">Unternehmensname *</Label>
                    <Input
                      data-testid="register-company-name-input"
                      id="companyName"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="Ihr Unternehmensname"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Telefon *</Label>
                    <Input
                      data-testid="register-phone-input"
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+49 123 456789"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="address">Geschäftsadresse</Label>
                    <Input
                      data-testid="register-address-input"
                      id="address"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="Straße, PLZ, Stadt"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="yardAddress">Hof-Adresse (für Abholung) *</Label>
                    <Input
                      data-testid="register-yard-address-input"
                      id="yardAddress"
                      value={yardAddress}
                      onChange={(e) => setYardAddress(e.target.value)}
                      placeholder="Adresse des Abschleppgeländes"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="yardLat">Breitengrad</Label>
                      <Input
                        data-testid="register-yard-lat-input"
                        id="yardLat"
                        type="number"
                        step="any"
                        value={yardLat}
                        onChange={(e) => setYardLat(e.target.value)}
                        placeholder="52.520008"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="yardLng">Längengrad</Label>
                      <Input
                        data-testid="register-yard-lng-input"
                        id="yardLng"
                        type="number"
                        step="any"
                        value={yardLng}
                        onChange={(e) => setYardLng(e.target.value)}
                        placeholder="13.404954"
                      />
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={getCurrentLocation}
                    className="w-full"
                  >
                    <MapPin className="h-4 w-4 mr-2" />
                    Aktuellen Standort verwenden
                  </Button>
                  <div className="space-y-2">
                    <Label htmlFor="openingHours">Öffnungszeiten *</Label>
                    <Input
                      data-testid="register-opening-hours-input"
                      id="openingHours"
                      value={openingHours}
                      onChange={(e) => setOpeningHours(e.target.value)}
                      placeholder="Mo-Fr 8:00-18:00, Sa 9:00-14:00"
                      required
                    />
                  </div>
                </>
              )}

              <Button
                data-testid="register-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-slate-900 hover:bg-slate-800 text-white font-medium"
              >
                {loading ? (
                  <div className="loading-spinner"></div>
                ) : (
                  'Registrieren'
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-slate-600">
              Bereits ein Konto?{' '}
              <Link to="/login" className="text-orange-600 hover:text-orange-700 font-medium">
                Jetzt anmelden
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RegisterPage;
