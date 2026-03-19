// Hook für Echtzeit-Benachrichtigungen bei neuen Aufträgen
import { useEffect, useRef, useCallback, useState } from 'react';
import { toast } from 'sonner';

// Alarm-Sound als Base64 (kurzer Notification-Sound)
const NOTIFICATION_SOUND = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleQkKZLft2aVmFwtNpejduXQSDS2N4urPgCMXM4Lg8tqLLBwwiODr1Y4vHyyA4vPYjS8dLH/k89eMLx0sf+Tz14wvHSx/5PPXjC8dLH/k89eMLx0sf+Tz14wvHSx/5PPXjC8dLH/k89eMLx0sf+Tz14wvHSx/5PPXjC8dLH/k89eMLx0rgOXz14suHCuB5fPWiy4cK4Hl89WLLhwrgeXz1YsuHCuB5fPViy4cK4Hl89WLLhwrgeXz1YsuHCuB5fPViy4cK4Hl89WLLhwrgeXz1YsuHCuB5fPViy4cK4Hl89WLLhwrgeXz1YsuHCuB5fTViy0cK4Lm9NWKLRwrg+f01YkuHCuE5/TUiS4cK4Xn89OILhwrhuf004guHCuG5/PTiC4cK4bn89OILhwrhuf004guHCuG5/PTiC4cK4bn89OILhwrhuf004guHCuF5/TTiC4cK4Xn9NSJLhsqhOf01YktGymD5vTVii0bKYLm9NaLLRspgeb01owtGymB5fTXjC0bKYDl9NiMLRspgOX02YwtGymA5fTZjC0bKX/l9NmMLRspf+X02YwtGyl/5fXZjC0bKX/l9dmMLRspf+X12YwtGyl/5fXZjC0bKX/l9dmMLRspf+X12YwtGyl/5fXZjC0cKX/l9diMLRwpgOX114wtHCmA5fXXjC0cKYDl9deMNR4phOj31oo2Hiuj7fzXiEMjLsb8/+GVZDpHqf7+5aFqQk2t//7lpGxETq///OSlbURPsP/85KVtRE+w//zkpW1ET7D//OSlbURPsP/85KVtRE+w//zkpW1ET7D//OSlbERPsP/846VtQ0+w//zjpW1DT7D//OOlbUNPsP/846VtQ0+w//zjpW1DT7D//OOlbUNPsP/846VtQ0+w//zjpW1DT7D//OOlbUNPsP/846VtQ0+w//zjpW1DT7D//OOlbUNPsP/846VtQ0+w//zjpW1DT7H/++OlbUNPsf/746VtQ0+x//vjpW1DT7H/++OlbUNPsf/746VtQ0+x//vjpW1DT7H/++OlbUNPsf/746VtQ0+x//vjpW1DT7H/++OlbUNPsf/746VtQ0+x//vjpW1DT7H/++OlbUNOsf/746VtQ06x//vjpW1DTrH/++KlbUNOsf/74qVtQ06x//vipW1DTrH/++KlbUNOsf/74qVtQ06x//vipW1DTrH/++KlbUNOsf/74qVtQ06x//vipW1DTrH/++KlbUNOsf/74qVtQ06x//vhpGxCTrD/+uGjbEJNr//64KNsQk2v//rgo2xCTK7/+t+jbEJMrv/636NsQkyu//rfo2xCTK7/+t+jbEJMrv/636NsQkyu//rfo2xCTK7/+t+jbEJMrv/636NsQkyu//rfo2xCTK7/+t+ia0JLrf/53qJrQkut//neomtCS63/+d6ia0JLrf/53qJrQkut//neomtCS63/+d6ia0JLrf/53qJrQkut//neomtCS63/+d6ia0JLrf/53qJrQkut//neomtCSqz/+N2hakJKrP/43aFqQkqr//jcoGpBSav/99yfaUFIqv/226BpQEip//baoGlAR6j/9dmfaD9Gp//12J5oPkWm//TYnmg+RaX/9NedaD5Fpf/015xnPUSk//PXm2Y9Q6P/89aaZjxCov/y1ZpmPEKh//LUmWU7QaD/8dOYZTpAn//w0phlOj+e/+/SmGQ6Pp3/7tCXYzg8m//tz5ZiNzqZ/+zNlWI2OZf/6syUYTU3lf/py5NgNDWT/+jKkmAzM5H/58mRXzIxjv/mx49eMC+M/+XGjlwuLIn/5MSMXC0qh//jwopcKyiE/+LBiVopJYL/4L+IWSclf//evYdXJCJ8/929hlYjIXn/3LuFVSEfdf/au4NUIx1z/9m5glMhG3D/2LeBUh8ZbP/Wtn9RHRdp/9S0fVAbFGb/0rJ7Txk=';

// Echtzeit-Benachrichtigungs-Hook
export const useJobNotifications = (jobs, enabled = true) => {
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [newJobsCount, setNewJobsCount] = useState(0);
  const previousJobIds = useRef(new Set());
  const audioRef = useRef(null);
  const isFirstLoad = useRef(true);

  // Audio-Element initialisieren
  useEffect(() => {
    audioRef.current = new Audio(NOTIFICATION_SOUND);
    audioRef.current.volume = 0.7;
    
    // Browser Notification Permission anfragen
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
    }
    
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  // Sound abspielen
  const playNotificationSound = useCallback(() => {
    if (soundEnabled && audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(err => {
        console.log('Audio playback failed:', err);
      });
    }
  }, [soundEnabled]);

  // Browser-Benachrichtigung senden
  const sendBrowserNotification = useCallback((title, body, jobData = null) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification(title, {
        body,
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        tag: 'new-job-notification',
        requireInteraction: true,
        vibrate: [200, 100, 200]
      });
      
      notification.onclick = () => {
        window.focus();
        notification.close();
      };
      
      // Auto-schließen nach 30 Sekunden
      setTimeout(() => notification.close(), 30000);
    }
  }, []);

  // Permission anfragen
  const requestNotificationPermission = useCallback(async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
      return permission === 'granted';
    }
    return false;
  }, []);

  // Neue Aufträge erkennen
  useEffect(() => {
    if (!enabled || !jobs || jobs.length === 0) return;
    
    const currentJobIds = new Set(jobs.map(job => job.id));
    
    // Beim ersten Laden nur die IDs speichern, nicht benachrichtigen
    if (isFirstLoad.current) {
      previousJobIds.current = currentJobIds;
      isFirstLoad.current = false;
      return;
    }
    
    // Neue Jobs finden (die noch nicht in previousJobIds sind)
    const newJobs = jobs.filter(job => 
      !previousJobIds.current.has(job.id) && 
      job.status === 'assigned' // Nur zugewiesene Aufträge
    );
    
    if (newJobs.length > 0) {
      setNewJobsCount(prev => prev + newJobs.length);
      
      // Sound abspielen
      playNotificationSound();
      
      // Für jeden neuen Auftrag eine Benachrichtigung
      newJobs.forEach(job => {
        // Toast-Benachrichtigung im Browser
        toast.success(
          <div className="flex flex-col gap-1">
            <span className="font-bold text-lg">🚨 Neuer Auftrag!</span>
            <span className="font-semibold">{job.license_plate}</span>
            <span className="text-sm text-gray-600">{job.location_address}</span>
            <span className="text-xs text-gray-500">{job.tow_reason}</span>
          </div>,
          {
            duration: 15000,
            position: 'top-center',
            style: {
              background: '#fef3c7',
              border: '2px solid #f59e0b',
              padding: '16px'
            }
          }
        );
        
        // Browser Push Notification
        sendBrowserNotification(
          '🚨 Neuer Abschleppauftrag!',
          `Kennzeichen: ${job.license_plate}\nStandort: ${job.location_address}`,
          job
        );
      });
    }
    
    // IDs aktualisieren
    previousJobIds.current = currentJobIds;
    
  }, [jobs, enabled, playNotificationSound, sendBrowserNotification]);

  // Zähler zurücksetzen
  const clearNewJobsCount = useCallback(() => {
    setNewJobsCount(0);
  }, []);

  return {
    notificationPermission,
    requestNotificationPermission,
    soundEnabled,
    setSoundEnabled,
    newJobsCount,
    clearNewJobsCount,
    playNotificationSound
  };
};

export default useJobNotifications;
