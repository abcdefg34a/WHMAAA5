import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Lock, ArrowLeft, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Password requirements check
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /\d/.test(password),
  };
  const allChecksPass = Object.values(passwordChecks).every(Boolean);

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setError('Kein Token vorhanden');
        setLoading(false);
        return;
      }

      try {
        const response = await axios.get(`${API}/auth/verify-reset-token/${token}`);
        setTokenValid(true);
        setEmail(response.data.email);
      } catch (err) {
        setError(err.response?.data?.detail || 'Ungültiger oder abgelaufener Link');
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!allChecksPass) {
      toast.error('Bitte erfüllen Sie alle Passwort-Anforderungen');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwörter stimmen nicht überein');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/auth/reset-password`, {
        token,
        new_password: password
      });
      setSuccess(true);
      toast.success('Passwort erfolgreich geändert');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Fehler beim Zurücksetzen');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (error || !tokenValid) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <CardTitle className="text-2xl">Ungültiger Link</CardTitle>
            <CardDescription>
              {error || 'Dieser Link zum Zurücksetzen des Passworts ist ungültig oder abgelaufen.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link to="/forgot-password">
              <Button className="w-full">
                Neuen Link anfordern
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Zurück zur Anmeldung
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Passwort geändert</CardTitle>
            <CardDescription>
              Ihr Passwort wurde erfolgreich geändert. Sie können sich jetzt mit Ihrem neuen Passwort anmelden.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/login">
              <Button className="w-full">
                Zur Anmeldung
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mb-4">
            <Lock className="h-8 w-8 text-orange-600" />
          </div>
          <CardTitle className="text-2xl">Neues Passwort setzen</CardTitle>
          <CardDescription>
            Erstellen Sie ein neues Passwort für <strong>{email}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">Neues Passwort</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Neues Passwort eingeben"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Password Requirements */}
            <div className="p-3 bg-slate-50 rounded-lg space-y-2 text-sm">
              <p className="font-medium text-slate-700">Passwort-Anforderungen:</p>
              <div className="grid grid-cols-2 gap-2">
                <div className={`flex items-center gap-2 ${passwordChecks.length ? 'text-green-600' : 'text-slate-400'}`}>
                  {passwordChecks.length ? <CheckCircle className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  Min. 8 Zeichen
                </div>
                <div className={`flex items-center gap-2 ${passwordChecks.uppercase ? 'text-green-600' : 'text-slate-400'}`}>
                  {passwordChecks.uppercase ? <CheckCircle className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  Großbuchstabe
                </div>
                <div className={`flex items-center gap-2 ${passwordChecks.lowercase ? 'text-green-600' : 'text-slate-400'}`}>
                  {passwordChecks.lowercase ? <CheckCircle className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  Kleinbuchstabe
                </div>
                <div className={`flex items-center gap-2 ${passwordChecks.number ? 'text-green-600' : 'text-slate-400'}`}>
                  {passwordChecks.number ? <CheckCircle className="h-4 w-4" /> : <div className="h-4 w-4 rounded-full border-2" />}
                  Zahl
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Passwort bestätigen</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Passwort erneut eingeben"
                required
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="text-sm text-red-500">Passwörter stimmen nicht überein</p>
              )}
            </div>

            <Button 
              type="submit" 
              className="w-full" 
              disabled={submitting || !allChecksPass || password !== confirmPassword}
            >
              {submitting ? 'Wird gespeichert...' : 'Passwort ändern'}
            </Button>

            <Link to="/login">
              <Button type="button" variant="ghost" className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Zurück zur Anmeldung
              </Button>
            </Link>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default ResetPasswordPage;
