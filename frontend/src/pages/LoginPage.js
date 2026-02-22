import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Car, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

export const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const user = await login(email, password);
      // Admin-only login page - reject non-admin users
      if (user.role !== 'admin') {
        setError('Diese Anmeldeseite ist nur für Administratoren. Bitte nutzen Sie das Portal unter /portal für Behörden und Abschleppdienste.');
        // Log them out since they used wrong login
        localStorage.removeItem('token');
        return;
      }
      navigate('/admin');
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
      <div className="w-full max-w-md">
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
              Admin-Anmeldung
            </CardTitle>
            <CardDescription>
              Nur für Administratoren - Behörden und Abschleppdienste nutzen bitte das <a href="/portal" className="text-orange-600 hover:text-orange-700">Portal</a>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div 
                  data-testid="login-error"
                  className="bg-red-50 text-red-700 px-4 py-3 rounded-md text-sm"
                >
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">E-Mail</Label>
                <Input
                  data-testid="login-email-input"
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ihre@email.de"
                  required
                  className="h-12"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Passwort</Label>
                  <Link to="/forgot-password" className="text-sm text-orange-600 hover:text-orange-700">
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

              <Button
                data-testid="login-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-slate-900 hover:bg-slate-800 text-white font-medium"
              >
                {loading ? (
                  <div className="loading-spinner"></div>
                ) : (
                  'Anmelden'
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-slate-600">
              Noch kein Konto?{' '}
              <Link to="/register" className="text-orange-600 hover:text-orange-700 font-medium">
                Jetzt registrieren
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
