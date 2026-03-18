import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Car, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { SkipLink } from '../components/accessibility';

export const LoginPage = () => {
  const navigate = useNavigate();
  const { login, logout, verify2FA } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // 2FA State
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (requires2FA) {
        // Step 2: Submit 2FA Code
        const user = await verify2FA(tempToken, totpCode);
        if (user.role !== 'admin') {
          setError('Diese Anmeldeseite ist nur für Administratoren.');
          logout();
          return;
        }
        navigate('/admin');
      } else {
        // Step 1: Submit Email/Password
        const response = await login(email, password);
        
        if (response.requires_2fa) {
          setRequires2FA(true);
          setTempToken(response.temp_token);
        } else {
          // Normal login
          if (response.role !== 'admin') {
            setError('Diese Anmeldeseite ist nur für Administratoren. Bitte nutzen Sie das Portal unter /portal für Behörden und Abschleppdienste.');
            logout();
            return;
          }
          navigate('/admin');
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Anmeldung fehlgeschlagen');
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
      {/* Skip-Link für Barrierefreiheit */}
      <SkipLink targetId="login-form" label="Zum Anmeldeformular springen" />
      
      <div className="w-full max-w-md">
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-8"
          aria-label="Zurück zur Startseite"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Zurück zur Startseite
        </Link>

        <Card className="shadow-xl border-slate-200" role="region" aria-label="Anmeldebereich">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="bg-slate-900 p-3 rounded-xl" aria-hidden="true">
                <Car className="h-8 w-8 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Admin-Anmeldung
            </CardTitle>
            <CardDescription>
              Nur für Administratoren - Behörden und Abschleppdienste nutzen bitte das <a href="/portal" className="text-orange-600 hover:text-orange-700 underline">Portal</a>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form id="login-form" onSubmit={handleSubmit} className="space-y-4" tabIndex={-1} aria-label="Anmeldeformular">
              {error && (
                <div 
                  data-testid="login-error"
                  className="bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm"
                  role="alert"
                  aria-live="assertive"
                >
                  {error}
                </div>
              )}

              {!requires2FA ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="email">E-Mail <span className="text-red-500" aria-hidden="true">*</span></Label>
                    <Input
                      data-testid="login-email-input"
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="ihre@email.de"
                      required
                      autoComplete="email"
                      className="h-12"
                      aria-required="true"
                      aria-describedby="email-hint"
                    />
                    <p id="email-hint" className="sr-only">Geben Sie Ihre E-Mail-Adresse ein</p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="password">Passwort <span className="text-red-500" aria-hidden="true">*</span></Label>
                      <Link to="/forgot-password" className="text-sm text-orange-600 hover:text-orange-700 underline underline-offset-2">
                        Passwort vergessen?
                      </Link>
                    </div>
                    <div className="relative">
                      <Input
                        data-testid="login-password-input"
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        autoComplete="current-password"
                        className="h-12 pr-12"
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
                </>
              ) : (
                <div className="space-y-4">
                  <div className="bg-blue-50 text-blue-800 p-4 rounded-lg text-sm mb-4">
                    Bitte geben Sie den 6-stelligen Code aus Ihrer Authenticator App ein.
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="totpCode">Authenticator Code</Label>
                    <Input
                      id="totpCode"
                      type="text"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      placeholder="123456"
                      required
                      autoComplete="one-time-code"
                      className="h-12 text-center text-xl tracking-widest"
                      maxLength={6}
                    />
                  </div>
                </div>
              )}

              <Button
                data-testid="login-submit-btn"
                type="submit"
                disabled={loading || (requires2FA && totpCode.length !== 6)}
                className="w-full h-12 bg-slate-900 hover:bg-slate-800 text-white font-medium mt-4"
              >
                {loading ? (
                  <div className="loading-spinner"></div>
                ) : (
                  requires2FA ? 'Verifizieren' : 'Anmelden'
                )}
              </Button>
              
              {requires2FA && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setRequires2FA(false);
                    setTotpCode('');
                  }}
                  className="w-full mt-2"
                >
                  Zurück
                </Button>
              )}
            </form>

            <div className="mt-6 text-center text-sm text-slate-600">
              Behörde oder Abschleppdienst?{' '}
              <Link to="/portal" className="text-orange-600 hover:text-orange-700 font-medium">
                Zum Portal
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
