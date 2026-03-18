import React, { useState } from 'react';
import axios from 'axios';
import { Shield, ShieldAlert, CheckCircle, Copy, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export const TwoFactorSetup = () => {
  const { user, updateUser } = useAuth();
  
  // States
  const [loading, setLoading] = useState(false);
  const [setupData, setSetupData] = useState(null); // { secret, qr_code }
  const [verificationCode, setVerificationCode] = useState('');
  
  const isEnabled = user?.totp_enabled;

  const initiateSetup = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/api/auth/2fa/setup`);
      setSetupData(response.data);
    } catch (error) {
      toast.error('Fehler beim Starten des 2FA Setups');
    } finally {
      setLoading(false);
    }
  };

  const verifySetup = async (e) => {
    e.preventDefault();
    if (verificationCode.length !== 6) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/api/auth/2fa/verify-setup`, { totp_code: verificationCode });
      toast.success('2-Faktor-Authentifizierung erfolgreich aktiviert!');
      // Update global user context immediately
      updateUser({ ...user, totp_enabled: true });
      setSetupData(null);
      setVerificationCode('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Falscher Code. Bitte versuchen Sie es erneut.');
    } finally {
      setLoading(false);
    }
  };

  const disable2FA = async (e) => {
    e.preventDefault();
    if (verificationCode.length !== 6) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/api/auth/2fa/disable`, { totp_code: verificationCode });
      toast.success('2-Faktor-Authentifizierung wurde deaktiviert.');
      updateUser({ ...user, totp_enabled: false });
      setVerificationCode('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Falscher Code. Deaktivierung fehlgeschlagen.');
    } finally {
      setLoading(false);
    }
  };

  const copySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      toast.success('Geheimschlüssel in die Zwischenablage kopiert');
    }
  };

  if (isEnabled) {
    return (
      <div className="bg-white border rounded-xl p-6 shadow-sm">
        <div className="flex items-start gap-4 mb-6">
          <div className="bg-green-100 p-3 rounded-full">
            <CheckCircle className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">2-Faktor-Authentifizierung aktiv</h3>
            <p className="text-slate-600 text-sm mt-1">
              Ihr Konto ist durch einen zusätzlichen Code aus Ihrer Authenticator-App geschützt.
            </p>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-6">
          <h4 className="font-medium text-slate-800 mb-4">2FA deaktivieren</h4>
          <p className="text-sm text-slate-600 mb-4">
            Um die 2-Faktor-Authentifizierung zu deaktivieren, geben Sie bitte den aktuellen 6-stelligen Code aus Ihrer App ein.
          </p>
          <form onSubmit={disable2FA} className="flex gap-3 max-w-sm">
            <Input
              type="text"
              placeholder="123456"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="text-center tracking-widest"
              maxLength={6}
            />
            <Button 
              type="submit" 
              variant="destructive"
              disabled={loading || verificationCode.length !== 6}
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Deaktivieren'}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  // Not enabled yet, and not in setup phase
  if (!setupData) {
    return (
      <div className="bg-white border rounded-xl p-6 shadow-sm">
        <div className="flex items-start gap-4 mb-6">
          <div className="bg-amber-100 p-3 rounded-full">
            <ShieldAlert className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">2-Faktor-Authentifizierung (2FA)</h3>
            <p className="text-slate-600 text-sm mt-1">
              Wir empfehlen dringend, Ihr Konto mit 2FA (z.B. Google Authenticator oder Authy) abzusichern.
            </p>
          </div>
        </div>
        
        <Button onClick={initiateSetup} disabled={loading} className="w-full sm:w-auto">
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Shield className="h-4 w-4 mr-2" />}
          2FA jetzt einrichten
        </Button>
      </div>
    );
  }

  // Setup phase
  return (
    <div className="bg-white border rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 border-b pb-4">
        2-Faktor-Authentifizierung einrichten
      </h3>
      
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row gap-8 items-start">
          <div className="w-full md:w-1/3 flex flex-col items-center">
            <div className="bg-slate-50 p-2 border rounded-lg inline-block mb-3">
              <img src={setupData.qr_code} alt="2FA QR Code" className="w-48 h-48" />
            </div>
            <p className="text-xs text-center text-slate-500">
              Scannen Sie diesen QR-Code mit Ihrer Authenticator App.
            </p>
          </div>
          
          <div className="w-full md:w-2/3 space-y-4">
            <div>
              <Label className="text-slate-700">Manuelle Eingabe (Alternativ)</Label>
              <div className="flex mt-1">
                <code className="bg-slate-100 px-3 py-2 rounded-l-md border border-r-0 flex-1 font-mono text-sm break-all">
                  {setupData.secret}
                </code>
                <Button 
                  type="button" 
                  variant="outline" 
                  className="rounded-l-none"
                  onClick={copySecret}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            <form onSubmit={verifySetup} className="bg-slate-50 p-4 border rounded-lg mt-6">
              <Label htmlFor="verificationCode" className="text-slate-700 font-semibold block mb-2">
                Schritt 3: Code bestätigen
              </Label>
              <p className="text-sm text-slate-600 mb-4">
                Geben Sie den 6-stelligen Code aus der App ein, um die Einrichtung abzuschließen.
              </p>
              
              <div className="flex gap-3">
                <Input
                  id="verificationCode"
                  type="text"
                  placeholder="123456"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="text-center tracking-widest text-lg h-12"
                  maxLength={6}
                  autoFocus
                />
                <Button 
                  type="submit" 
                  className="h-12 px-6"
                  disabled={loading || verificationCode.length !== 6}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Aktivieren'}
                </Button>
              </div>
            </form>
          </div>
        </div>
        
        <div className="pt-4 border-t">
          <Button 
            type="button" 
            variant="ghost" 
            onClick={() => setSetupData(null)}
          >
            Abbrechen
          </Button>
        </div>
      </div>
    </div>
  );
};

export default TwoFactorSetup;
