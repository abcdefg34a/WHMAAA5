import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Car, Eye, EyeOff, ArrowLeft, Shield, Truck, Upload, Euro, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';

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
  const [openingHours, setOpeningHours] = useState('');
  // NEW: Cost fields
  const [towCost, setTowCost] = useState('');
  const [dailyCost, setDailyCost] = useState('');
  // NEW: Business license
  const [businessLicense, setBusinessLicense] = useState('');
  const [businessLicenseFileName, setBusinessLicenseFileName] = useState('');

  // Password validation
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /\d/.test(password),
  };
  const allPasswordChecksPass = Object.values(passwordChecks).every(Boolean);

  useEffect(() => {
    const role = searchParams.get('role');
    if (role && (role === 'authority' || role === 'towing_service')) {
      setActiveTab(role);
    }
  }, [searchParams]);

  const handleBusinessLicenseUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Datei zu groß. Maximal 5MB erlaubt.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setBusinessLicense(event.target.result);
      setBusinessLicenseFileName(file.name);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate password
    if (!allPasswordChecksPass) {
      setError('Bitte erfüllen Sie alle Passwort-Anforderungen');
      setLoading(false);
      return;
    }

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
        if (!businessLicense) {
          setError('Bitte laden Sie einen Gewerbenachweis hoch');
          setLoading(false);
          return;
        }
        data.company_name = companyName;
        data.phone = phone;
        data.address = address;
        data.yard_address = yardAddress;
        data.opening_hours = openingHours;
        data.tow_cost = towCost ? parseFloat(towCost) : 0;
        data.daily_cost = dailyCost ? parseFloat(dailyCost) : 0;
        data.business_license = businessLicense;
      }

      await register(data);
      
      // This code will only run for roles that don't need approval (e.g., admin)
      if (activeTab === 'authority') {
        navigate('/authority');
      } else if (activeTab === 'towing_service') {
        navigate('/towing');
      }
    } catch (err) {
      // Check if it's a 202 "Accepted" response (needs approval)
      if (err.response?.status === 202) {
        toast.success('Registrierung erfolgreich!', {
          description: 'Ihr Konto muss erst von einem Administrator freigeschaltet werden. Sie werden benachrichtigt, sobald Ihr Konto aktiviert wurde.',
          duration: 8000
        });
        navigate('/login');
      } else {
        setError(err.response?.data?.detail || 'Registrierung fehlgeschlagen');
      }
    } finally {
      setLoading(false);
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
                {/* Password Requirements */}
                {password && (
                  <div className="p-3 bg-slate-50 rounded-lg space-y-2 text-xs">
                    <p className="font-medium text-slate-600">Passwort-Anforderungen:</p>
                    <div className="grid grid-cols-2 gap-1">
                      <div className={`flex items-center gap-1.5 ${passwordChecks.length ? 'text-green-600' : 'text-slate-400'}`}>
                        {passwordChecks.length ? <CheckCircle className="h-3 w-3" /> : <div className="h-3 w-3 rounded-full border" />}
                        Min. 8 Zeichen
                      </div>
                      <div className={`flex items-center gap-1.5 ${passwordChecks.uppercase ? 'text-green-600' : 'text-slate-400'}`}>
                        {passwordChecks.uppercase ? <CheckCircle className="h-3 w-3" /> : <div className="h-3 w-3 rounded-full border" />}
                        Großbuchstabe
                      </div>
                      <div className={`flex items-center gap-1.5 ${passwordChecks.lowercase ? 'text-green-600' : 'text-slate-400'}`}>
                        {passwordChecks.lowercase ? <CheckCircle className="h-3 w-3" /> : <div className="h-3 w-3 rounded-full border" />}
                        Kleinbuchstabe
                      </div>
                      <div className={`flex items-center gap-1.5 ${passwordChecks.number ? 'text-green-600' : 'text-slate-400'}`}>
                        {passwordChecks.number ? <CheckCircle className="h-3 w-3" /> : <div className="h-3 w-3 rounded-full border" />}
                        Zahl
                      </div>
                    </div>
                  </div>
                )}
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

                  {/* NEW: Cost fields */}
                  <div className="border-t pt-4 mt-4">
                    <h3 className="font-medium text-slate-900 mb-3 flex items-center gap-2">
                      <Euro className="h-4 w-4" />
                      Kosten (können später angepasst werden)
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor="towCost">Anfahrtskosten (€)</Label>
                        <Input
                          data-testid="register-tow-cost-input"
                          id="towCost"
                          type="number"
                          step="0.01"
                          min="0"
                          value={towCost}
                          onChange={(e) => setTowCost(e.target.value)}
                          placeholder="150.00"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="dailyCost">Standkosten/Tag (€)</Label>
                        <Input
                          data-testid="register-daily-cost-input"
                          id="dailyCost"
                          type="number"
                          step="0.01"
                          min="0"
                          value={dailyCost}
                          onChange={(e) => setDailyCost(e.target.value)}
                          placeholder="20.00"
                        />
                      </div>
                    </div>
                  </div>

                  {/* NEW: Business License Upload */}
                  <div className="border-t pt-4 mt-4">
                    <h3 className="font-medium text-slate-900 mb-3 flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      Gewerbenachweis *
                    </h3>
                    <div className="space-y-2">
                      <div 
                        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                          businessLicense ? 'border-green-500 bg-green-50' : 'border-slate-300 hover:border-slate-400'
                        }`}
                        onClick={() => document.getElementById('businessLicenseInput').click()}
                      >
                        {businessLicense ? (
                          <div className="text-green-700">
                            <Upload className="h-8 w-8 mx-auto mb-2" />
                            <p className="font-medium">{businessLicenseFileName}</p>
                            <p className="text-sm">Klicken zum Ändern</p>
                          </div>
                        ) : (
                          <div className="text-slate-500">
                            <Upload className="h-8 w-8 mx-auto mb-2" />
                            <p className="font-medium">Gewerbenachweis hochladen</p>
                            <p className="text-sm">PDF, JPG oder PNG (max. 5MB)</p>
                          </div>
                        )}
                      </div>
                      <input
                        id="businessLicenseInput"
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={handleBusinessLicenseUpload}
                        className="hidden"
                      />
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                    <p className="font-medium">Hinweis zur Freischaltung</p>
                    <p>Nach der Registrierung wird Ihr Konto von einem Administrator geprüft und freigeschaltet.</p>
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
