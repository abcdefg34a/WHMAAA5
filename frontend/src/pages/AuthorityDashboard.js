import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { 
  Car, MapPin, Camera, Plus, LogOut, FileText, Menu, X, 
  Search, Clock, ChevronRight, Trash2, Link as LinkIcon, CheckCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { toast } from 'sonner';
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

// Location Picker Component
const LocationPicker = ({ position, setPosition }) => {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });

  return position ? <Marker position={position} /> : null;
};

export const AuthorityDashboard = () => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('new');
  const [jobs, setJobs] = useState([]);
  const [linkedServices, setLinkedServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [serviceCodeInput, setServiceCodeInput] = useState('');
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);

  // New job form state
  const [licensePlate, setLicensePlate] = useState('');
  const [vin, setVin] = useState('');
  const [towReason, setTowReason] = useState('');
  const [locationAddress, setLocationAddress] = useState('');
  const [position, setPosition] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [notes, setNotes] = useState('');
  const [selectedServiceId, setSelectedServiceId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchJobs();
    fetchLinkedServices();
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/jobs`);
      setJobs(response.data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchLinkedServices = async () => {
    try {
      const response = await axios.get(`${API}/services`);
      setLinkedServices(response.data);
    } catch (error) {
      console.error('Error fetching services:', error);
    }
  };

  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude } = pos.coords;
          setPosition([latitude, longitude]);
          
          // Reverse geocoding
          try {
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
            );
            const data = await response.json();
            setLocationAddress(data.display_name || `${latitude}, ${longitude}`);
          } catch {
            setLocationAddress(`${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
          }
        },
        (error) => {
          toast.error('Standort konnte nicht ermittelt werden');
        }
      );
    }
  };

  const handlePhotoUpload = (e) => {
    const files = Array.from(e.target.files);
    if (photos.length + files.length > 5) {
      toast.error('Maximal 5 Fotos erlaubt');
      return;
    }

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPhotos(prev => [...prev, e.target.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removePhoto = (index) => {
    setPhotos(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmitJob = async (e) => {
    e.preventDefault();
    
    if (!licensePlate || !towReason || !position) {
      toast.error('Bitte füllen Sie alle Pflichtfelder aus');
      return;
    }

    setSubmitting(true);
    try {
      const jobData = {
        license_plate: licensePlate.toUpperCase(),
        vin: vin || null,
        tow_reason: towReason,
        location_address: locationAddress,
        location_lat: position[0],
        location_lng: position[1],
        photos: photos,
        notes: notes || null,
        assigned_service_id: selectedServiceId || null
      };

      await axios.post(`${API}/jobs`, jobData);
      toast.success('Auftrag erfolgreich erstellt');
      
      // Reset form
      setLicensePlate('');
      setVin('');
      setTowReason('');
      setLocationAddress('');
      setPosition(null);
      setPhotos([]);
      setNotes('');
      setSelectedServiceId('');
      
      fetchJobs();
      setActiveTab('jobs');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Erstellen des Auftrags');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLinkService = async () => {
    if (!serviceCodeInput.trim()) return;
    
    try {
      const response = await axios.post(`${API}/services/link`, { service_code: serviceCodeInput });
      toast.success(`${response.data.service_name} erfolgreich verknüpft`);
      setServiceCodeInput('');
      setLinkDialogOpen(false);
      fetchLinkedServices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Verknüpfen');
    }
  };

  const handleUnlinkService = async (serviceId) => {
    try {
      await axios.delete(`${API}/services/unlink/${serviceId}`);
      toast.success('Abschleppdienst entfernt');
      fetchLinkedServices();
    } catch (error) {
      toast.error('Fehler beim Entfernen');
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { label: 'Ausstehend', class: 'status-pending' },
      assigned: { label: 'Zugewiesen', class: 'status-assigned' },
      on_site: { label: 'Vor Ort', class: 'status-on_site' },
      towed: { label: 'Abgeschleppt', class: 'status-towed' },
      in_yard: { label: 'Im Hof', class: 'status-in_yard' },
      released: { label: 'Abgeholt', class: 'status-released' }
    };
    const config = statusConfig[status] || { label: status, class: 'bg-gray-500' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.class}`}>
        {config.label}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Car className="h-8 w-8 text-slate-900" />
              <div className="hidden sm:block">
                <h1 className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Behörden-Dashboard
                </h1>
                <p className="text-xs text-slate-500">{user?.authority_name}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="hidden md:block text-sm text-slate-600">
                {user?.name}
              </span>
              <Button
                data-testid="logout-btn"
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Abmelden</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-new-job" value="new" className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Neuer Auftrag
            </TabsTrigger>
            <TabsTrigger data-testid="tab-my-jobs" value="jobs" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Meine Aufträge
            </TabsTrigger>
            <TabsTrigger data-testid="tab-services" value="services" className="flex items-center gap-2">
              <LinkIcon className="h-4 w-4" />
              Abschleppdienste
            </TabsTrigger>
          </TabsList>

          {/* New Job Tab */}
          <TabsContent value="new">
            <form onSubmit={handleSubmitJob}>
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Vehicle Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Car className="h-5 w-5" />
                      Fahrzeugdaten
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="licensePlate">Kennzeichen *</Label>
                      <Input
                        data-testid="job-license-plate-input"
                        id="licensePlate"
                        value={licensePlate}
                        onChange={(e) => setLicensePlate(e.target.value.toUpperCase())}
                        placeholder="B-AB 1234"
                        className="license-plate-input text-xl"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="vin">Fahrzeug-Identifizierungsnummer (FIN)</Label>
                      <Input
                        data-testid="job-vin-input"
                        id="vin"
                        value={vin}
                        onChange={(e) => setVin(e.target.value.toUpperCase())}
                        placeholder="WVWZZZ3CZWE123456"
                        className="font-mono"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="towReason">Abschleppgrund *</Label>
                      <Select value={towReason} onValueChange={setTowReason} required>
                        <SelectTrigger data-testid="job-tow-reason-select">
                          <SelectValue placeholder="Grund auswählen" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Parken im absoluten Halteverbot">Parken im absoluten Halteverbot</SelectItem>
                          <SelectItem value="Parken auf Behindertenparkplatz">Parken auf Behindertenparkplatz</SelectItem>
                          <SelectItem value="Parken auf Feuerwehrzufahrt">Parken auf Feuerwehrzufahrt</SelectItem>
                          <SelectItem value="Parken auf Gehweg">Parken auf Gehweg</SelectItem>
                          <SelectItem value="Unerlaubtes Parken">Unerlaubtes Parken</SelectItem>
                          <SelectItem value="Verkehrsbehinderung">Verkehrsbehinderung</SelectItem>
                          <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="notes">Bemerkungen</Label>
                      <Textarea
                        data-testid="job-notes-input"
                        id="notes"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Zusätzliche Informationen..."
                        rows={3}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Location */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MapPin className="h-5 w-5" />
                      Standort
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button
                      data-testid="get-location-btn"
                      type="button"
                      onClick={handleGetLocation}
                      variant="outline"
                      className="w-full"
                    >
                      <MapPin className="h-4 w-4 mr-2" />
                      Aktuellen Standort erfassen
                    </Button>
                    <div className="space-y-2">
                      <Label htmlFor="locationAddress">Adresse *</Label>
                      <Input
                        data-testid="job-location-address-input"
                        id="locationAddress"
                        value={locationAddress}
                        onChange={(e) => setLocationAddress(e.target.value)}
                        placeholder="Straße, Hausnummer, PLZ, Stadt"
                        required
                      />
                    </div>
                    <div className="map-container h-48">
                      <MapContainer
                        center={position || [52.520008, 13.404954]}
                        zoom={position ? 16 : 10}
                        scrollWheelZoom={true}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <LocationPicker position={position} setPosition={(pos) => {
                          setPosition(pos);
                          setLocationAddress(`${pos[0].toFixed(6)}, ${pos[1].toFixed(6)}`);
                        }} />
                      </MapContainer>
                    </div>
                    <p className="text-xs text-slate-500">
                      Klicken Sie auf die Karte, um den Standort manuell zu setzen
                    </p>
                  </CardContent>
                </Card>

                {/* Photos */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Camera className="h-5 w-5" />
                      Fotos ({photos.length}/5)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="photo-upload-grid">
                      {[...Array(5)].map((_, index) => (
                        <div
                          key={index}
                          className="photo-upload-slot"
                          onClick={() => index >= photos.length && fileInputRef.current?.click()}
                        >
                          {photos[index] ? (
                            <div className="relative w-full h-full group">
                              <img src={photos[index]} alt={`Foto ${index + 1}`} />
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removePhoto(index);
                                }}
                                className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          ) : (
                            <Camera className="h-6 w-6 text-slate-400" />
                          )}
                        </div>
                      ))}
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      capture="environment"
                      multiple
                      onChange={handlePhotoUpload}
                      className="hidden"
                    />
                  </CardContent>
                </Card>

                {/* Assign Service */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <LinkIcon className="h-5 w-5" />
                      Abschleppdienst zuweisen
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {linkedServices.length > 0 ? (
                      <Select value={selectedServiceId} onValueChange={setSelectedServiceId}>
                        <SelectTrigger data-testid="job-service-select">
                          <SelectValue placeholder="Abschleppdienst auswählen" />
                        </SelectTrigger>
                        <SelectContent>
                          {linkedServices.map(service => (
                            <SelectItem key={service.id} value={service.id}>
                              {service.company_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-slate-500 mb-3">Keine Abschleppdienste verknüpft</p>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setActiveTab('services')}
                        >
                          Abschleppdienst hinzufügen
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="mt-6">
                <Button
                  data-testid="submit-job-btn"
                  type="submit"
                  disabled={submitting}
                  className="w-full md:w-auto h-12 px-8 bg-slate-900 hover:bg-slate-800 text-white"
                >
                  {submitting ? (
                    <div className="loading-spinner mr-2"></div>
                  ) : (
                    <CheckCircle className="h-5 w-5 mr-2" />
                  )}
                  Auftrag erstellen
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* Jobs Tab */}
          <TabsContent value="jobs">
            <Card>
              <CardHeader>
                <CardTitle>Meine Aufträge</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="empty-state">
                    <FileText className="empty-state-icon" />
                    <p>Noch keine Aufträge erstellt</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {jobs.map(job => (
                      <div key={job.id} className="job-card">
                        <div className="job-card-header">
                          <div>
                            <p className="job-license-plate">{job.license_plate}</p>
                            <p className="text-sm text-slate-500">{job.job_number}</p>
                          </div>
                          {getStatusBadge(job.status)}
                        </div>
                        <div className="grid sm:grid-cols-2 gap-3 text-sm">
                          <div className="flex items-center gap-2 text-slate-600">
                            <MapPin className="h-4 w-4" />
                            <span className="truncate">{job.location_address}</span>
                          </div>
                          <div className="flex items-center gap-2 text-slate-600">
                            <Clock className="h-4 w-4" />
                            <span>{new Date(job.created_at).toLocaleString('de-DE')}</span>
                          </div>
                        </div>
                        {job.assigned_service_name && (
                          <p className="mt-2 text-sm text-slate-600">
                            Zugewiesen an: <span className="font-medium">{job.assigned_service_name}</span>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Services Tab */}
          <TabsContent value="services">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Verknüpfte Abschleppdienste</CardTitle>
                <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
                  <DialogTrigger asChild>
                    <Button data-testid="add-service-btn" className="bg-slate-900 hover:bg-slate-800">
                      <Plus className="h-4 w-4 mr-2" />
                      Hinzufügen
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Abschleppdienst verknüpfen</DialogTitle>
                      <DialogDescription>
                        Geben Sie den 6-stelligen Code des Abschleppdienstes ein
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <Input
                        data-testid="service-code-input"
                        value={serviceCodeInput}
                        onChange={(e) => setServiceCodeInput(e.target.value)}
                        placeholder="z.B. AbCd12"
                        className="text-center font-mono text-lg uppercase"
                        maxLength={6}
                      />
                      <Button
                        data-testid="link-service-btn"
                        onClick={handleLinkService}
                        className="w-full bg-slate-900 hover:bg-slate-800"
                        disabled={serviceCodeInput.length !== 6}
                      >
                        Verknüpfen
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {linkedServices.length === 0 ? (
                  <div className="empty-state">
                    <LinkIcon className="empty-state-icon" />
                    <p>Noch keine Abschleppdienste verknüpft</p>
                    <p className="text-sm mt-2">
                      Bitten Sie Ihren Abschleppdienst um den 6-stelligen Verknüpfungscode
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {linkedServices.map(service => (
                      <div 
                        key={service.id} 
                        className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium">{service.company_name}</p>
                          <p className="text-sm text-slate-500">{service.phone}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUnlinkService(service.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default AuthorityDashboard;
