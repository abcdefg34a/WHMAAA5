import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Car, Shield, Truck, UserPlus, LogIn, ArrowLeft, Eye, EyeOff, Building2, Phone, MapPin, User, FileText, Upload, X, Image } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const PortalPage = () => {
  const navigate = useNavigate();
  const { login, logout } = useAuth();
  
  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Register state
  const [registerRole, setRegisterRole] = useState('authority');
  const [registerData, setRegisterData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    // Authority fields
    authority_name: '',
    // Towing service fields
    company_name: '',
    address: '',
    phone: '',
    business_license: ''  // Gewerbenachweis
  });
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState('');
  const [businessLicenseImage, setBusinessLicenseImage] = useState(null);
  const businessLicenseInputRef = useRef(null);

  // Handle business license photo upload
  const handleBusinessLicenseUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Datei zu groß. Maximal 5MB erlaubt.');
      return;
    }

    // Check file type
    if (!file.type.startsWith('image/')) {
      toast.error('Bitte nur Bilddateien hochladen (JPG, PNG, etc.)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setBusinessLicenseImage(event.target.result);
      setRegisterData(prev => ({...prev, business_license: event.target.result}));
    };
    reader.readAsDataURL(file);
  };

  const removeBusinessLicenseImage = () => {
    setBusinessLicenseImage(null);
    setRegisterData(prev => ({...prev, business_license: ''}));
    if (businessLicenseInputRef.current) {
      businessLicenseInputRef.current.value = '';
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    try {
      const user = await login(loginEmail, loginPassword);
      
      // Portal is ONLY for authority and towing_service - reject admins
      if (user.role === 'admin') {
        setLoginError('Administratoren nutzen bitte die Admin-Anmeldeseite unter /login');
        logout(); // Properly clear token and user state
        return;
      }
      
      // Redirect based on role
      if (user.role === 'authority') {
        navigate('/authority');
      } else if (user.role === 'towing_service') {
        navigate('/towing');
      }
    } catch (err) {
      setLoginError(err.response?.data?.detail || 'Anmeldung fehlgeschlagen');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegisterLoading(true);
    setRegisterError('');

    if (registerData.password !== registerData.confirmPassword) {
      setRegisterError('Passwörter stimmen nicht überein');
      setRegisterLoading(false);
      return;
    }

    if (registerData.password.length < 8) {
      setRegisterError('Passwort muss mindestens 8 Zeichen haben');
      setRegisterLoading(false);
      return;
    }

    // Validate business license for towing services
    if (registerRole === 'towing_service' && !businessLicenseImage) {
      setRegisterError('Bitte laden Sie ein Foto Ihres Gewerbescheins hoch');
      setRegisterLoading(false);
      return;
    }

    try {
      const payload = {
        name: registerData.name,
        email: registerData.email,
        password: registerData.password,
        role: registerRole
      };

      if (registerRole === 'authority') {
        payload.authority_name = registerData.authority_name;
      } else {
        payload.company_name = registerData.company_name;
        payload.address = registerData.address;
        payload.phone = registerData.phone;
        payload.business_license = registerData.business_license;
      }

      await axios.post(`${API_URL}/api/auth/register`, payload);
      toast.success('Registrierung erfolgreich! Ein Administrator wird Ihren Account freischalten.');
      // Reset form
      setRegisterData({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        authority_name: '',
        company_name: '',
        address: '',
        phone: ''
      });
    } catch (err) {
      setRegisterError(err.response?.data?.detail || 'Registrierung fehlgeschlagen');
    } finally {
      setRegisterLoading(false);
    }
  };

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
      <main className="max-w-2xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Chivo, sans-serif' }}>
            Portal für Behörden & Abschleppdienste
          </h1>
          <p className="text-slate-600">
            Melden Sie sich an oder erstellen Sie einen neuen Account
          </p>
        </div>

        <Card className="shadow-xl">
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login" className="flex items-center gap-2">
                <LogIn className="h-4 w-4" />
                Anmelden
              </TabsTrigger>
              <TabsTrigger value="register" className="flex items-center gap-2">
                <UserPlus className="h-4 w-4" />
                Registrieren
              </TabsTrigger>
            </TabsList>

            {/* Login Tab */}
            <TabsContent value="login">
              <CardHeader>
                <CardTitle>Anmelden</CardTitle>
                <CardDescription>
                  Für Behörden und Abschleppdienste
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleLogin} className="space-y-4">
                  {loginError && (
                    <div className="bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm">
                      {loginError}
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="login-email">E-Mail</Label>
                    <Input
                      id="login-email"
                      type="email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="ihre@email.de"
                      required
                      autoComplete="email"
                      className="h-12"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="login-password">Passwort</Label>
                    <div className="relative">
                      <Input
                        id="login-password"
                        type={showLoginPassword ? 'text' : 'password'}
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        autoComplete="current-password"
                        className="h-12 pr-12"
                      />
                      <button
                        type="button"
                        onClick={() => setShowLoginPassword(!showLoginPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showLoginPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={loginLoading}
                    className="w-full h-12 bg-slate-900 hover:bg-slate-800"
                  >
                    {loginLoading ? (
                      <div className="loading-spinner"></div>
                    ) : (
                      <>
                        <LogIn className="h-4 w-4 mr-2" />
                        Anmelden
                      </>
                    )}
                  </Button>

                  <div className="text-center">
                    <a href="/forgot-password" className="text-sm text-orange-600 hover:text-orange-700">
                      Passwort vergessen?
                    </a>
                  </div>
                </form>
              </CardContent>
            </TabsContent>

            {/* Register Tab */}
            <TabsContent value="register">
              <CardHeader>
                <CardTitle>Registrieren</CardTitle>
                <CardDescription>
                  Erstellen Sie einen neuen Account
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleRegister} className="space-y-4">
                  {registerError && (
                    <div className="bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm">
                      {registerError}
                    </div>
                  )}

                  {/* Role Selection */}
                  <div className="space-y-2">
                    <Label>Ich bin...</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setRegisterRole('authority')}
                        className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-colors ${
                          registerRole === 'authority' 
                            ? 'border-amber-500 bg-amber-50' 
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <Shield className={`h-6 w-6 ${registerRole === 'authority' ? 'text-amber-600' : 'text-slate-400'}`} />
                        <span className={`font-medium ${registerRole === 'authority' ? 'text-amber-700' : 'text-slate-600'}`}>
                          Behörde
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setRegisterRole('towing_service')}
                        className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-colors ${
                          registerRole === 'towing_service' 
                            ? 'border-orange-500 bg-orange-50' 
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <Truck className={`h-6 w-6 ${registerRole === 'towing_service' ? 'text-orange-600' : 'text-slate-400'}`} />
                        <span className={`font-medium ${registerRole === 'towing_service' ? 'text-orange-700' : 'text-slate-600'}`}>
                          Abschleppdienst
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Common Fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="register-name">
                        <User className="h-3 w-3 inline mr-1" />
                        Ansprechpartner
                      </Label>
                      <Input
                        id="register-name"
                        value={registerData.name}
                        onChange={(e) => setRegisterData({...registerData, name: e.target.value})}
                        placeholder="Max Mustermann"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-email">E-Mail</Label>
                      <Input
                        id="register-email"
                        type="email"
                        value={registerData.email}
                        onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                        placeholder="kontakt@firma.de"
                        required
                      />
                    </div>
                  </div>

                  {/* Role-specific Fields */}
                  {registerRole === 'authority' ? (
                    <div className="space-y-2">
                      <Label htmlFor="authority-name">
                        <Building2 className="h-3 w-3 inline mr-1" />
                        Behördenname
                      </Label>
                      <Input
                        id="authority-name"
                        value={registerData.authority_name}
                        onChange={(e) => setRegisterData({...registerData, authority_name: e.target.value})}
                        placeholder="z.B. Ordnungsamt Berlin-Mitte"
                        required
                      />
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="company-name">
                          <Truck className="h-3 w-3 inline mr-1" />
                          Firmenname
                        </Label>
                        <Input
                          id="company-name"
                          value={registerData.company_name}
                          onChange={(e) => setRegisterData({...registerData, company_name: e.target.value})}
                          placeholder="z.B. Müller Abschleppdienst GmbH"
                          required
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="address">
                            <MapPin className="h-3 w-3 inline mr-1" />
                            Adresse
                          </Label>
                          <Input
                            id="address"
                            value={registerData.address}
                            onChange={(e) => setRegisterData({...registerData, address: e.target.value})}
                            placeholder="Straße, PLZ Ort"
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="phone">
                            <Phone className="h-3 w-3 inline mr-1" />
                            Telefon
                          </Label>
                          <Input
                            id="phone"
                            type="tel"
                            value={registerData.phone}
                            onChange={(e) => setRegisterData({...registerData, phone: e.target.value})}
                            placeholder="+49 123 456789"
                            required
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>
                          <FileText className="h-3 w-3 inline mr-1" />
                          Gewerbenachweis (Foto)
                        </Label>
                        
                        {/* Hidden file input */}
                        <input
                          type="file"
                          ref={businessLicenseInputRef}
                          onChange={handleBusinessLicenseUpload}
                          accept="image/*"
                          className="hidden"
                        />
                        
                        {!businessLicenseImage ? (
                          <div 
                            onClick={() => businessLicenseInputRef.current?.click()}
                            className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center cursor-pointer hover:border-orange-400 hover:bg-orange-50 transition-colors"
                          >
                            <Upload className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                            <p className="text-sm font-medium text-slate-600">Gewerbenachweis hochladen</p>
                            <p className="text-xs text-slate-500 mt-1">Klicken oder Foto hierher ziehen</p>
                            <p className="text-xs text-slate-400 mt-1">JPG, PNG (max. 5MB)</p>
                          </div>
                        ) : (
                          <div className="relative border rounded-lg overflow-hidden">
                            <img 
                              src={businessLicenseImage} 
                              alt="Gewerbenachweis" 
                              className="w-full h-40 object-cover"
                            />
                            <button
                              type="button"
                              onClick={removeBusinessLicenseImage}
                              className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600"
                            >
                              <X className="h-4 w-4" />
                            </button>
                            <div className="absolute bottom-0 left-0 right-0 bg-green-500 text-white text-xs py-1 px-2 flex items-center gap-1">
                              <Image className="h-3 w-3" />
                              Gewerbenachweis hochgeladen
                            </div>
                          </div>
                        )}
                        <p className="text-xs text-slate-500">Bitte laden Sie ein Foto Ihres Gewerbescheins oder Handelsregisterauszugs hoch</p>
                      </div>
                    </>
                  )}

                  {/* Password Fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="register-password">Passwort</Label>
                      <div className="relative">
                        <Input
                          id="register-password"
                          type={showRegisterPassword ? 'text' : 'password'}
                          value={registerData.password}
                          onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                          placeholder="Min. 8 Zeichen"
                          required
                          autoComplete="new-password"
                          className="pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                          {showRegisterPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-password">Passwort bestätigen</Label>
                      <Input
                        id="confirm-password"
                        type="password"
                        value={registerData.confirmPassword}
                        onChange={(e) => setRegisterData({...registerData, confirmPassword: e.target.value})}
                        placeholder="Passwort wiederholen"
                        required
                        autoComplete="new-password"
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={registerLoading}
                    className={`w-full h-12 ${
                      registerRole === 'authority' 
                        ? 'bg-amber-600 hover:bg-amber-700' 
                        : 'bg-orange-600 hover:bg-orange-700'
                    }`}
                  >
                    {registerLoading ? (
                      <div className="loading-spinner"></div>
                    ) : (
                      <>
                        <UserPlus className="h-4 w-4 mr-2" />
                        {registerRole === 'authority' ? 'Als Behörde registrieren' : 'Als Abschleppdienst registrieren'}
                      </>
                    )}
                  </Button>

                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-xs text-blue-800 text-center">
                      <strong>Hinweis:</strong> Neue Registrierungen müssen von einem Administrator freigegeben werden.
                    </p>
                  </div>
                </form>
              </CardContent>
            </TabsContent>
          </Tabs>
        </Card>

        {/* Role Info Cards */}
        <div className="grid md:grid-cols-2 gap-4 mt-8">
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Shield className="h-5 w-5 text-amber-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-amber-900 mb-1">Für Behörden</h3>
                  <p className="text-sm text-amber-700">
                    Ordnungsämter und Polizei erstellen hier Abschleppaufträge.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-orange-50 border-orange-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Truck className="h-5 w-5 text-orange-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-orange-900 mb-1">Für Abschleppdienste</h3>
                  <p className="text-sm text-orange-700">
                    Abschleppunternehmen nehmen Aufträge an und verwalten Fahrzeuge.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
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
