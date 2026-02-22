import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { 
  Car, MapPin, Camera, Plus, LogOut, FileText, Menu, X, 
  Search, Clock, ChevronRight, Trash2, Link as LinkIcon, CheckCircle,
  Users, UserPlus, Lock, Unlock, Key, Badge, Download, Filter, Calendar
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { toast } from 'sonner';
import { Pagination } from '../components/Pagination';
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

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const itemsPerPage = 50;

  // NEW: Filter state
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterService, setFilterService] = useState('all');

  // Employee management state
  const [employees, setEmployees] = useState([]);
  const [employeeDialogOpen, setEmployeeDialogOpen] = useState(false);
  const [newEmployeeName, setNewEmployeeName] = useState('');
  const [newEmployeeEmail, setNewEmployeeEmail] = useState('');
  const [newEmployeePassword, setNewEmployeePassword] = useState('');
  const [creatingEmployee, setCreatingEmployee] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [newPassword, setNewPassword] = useState('');

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

  // NEW: Job type and Sicherstellung fields
  const [jobType, setJobType] = useState('towing');
  const [sicherstellungReason, setSicherstellungReason] = useState('');
  const [vehicleCategory, setVehicleCategory] = useState('under_3_5t');
  const [orderingAuthority, setOrderingAuthority] = useState('');
  const [contactAttempts, setContactAttempts] = useState(false);
  const [contactAttemptsNotes, setContactAttemptsNotes] = useState('');
  const [estimatedVehicleValue, setEstimatedVehicleValue] = useState('');

  useEffect(() => {
    fetchJobs();
    fetchLinkedServices();
    if (user?.is_main_authority) {
      fetchEmployees();
    }
  }, [user, currentPage, filterStatus, filterDateFrom, filterDateTo, filterService]);

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());
      
      // Add filter params
      if (filterStatus && filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterDateFrom) {
        params.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        params.append('date_to', filterDateTo);
      }
      if (filterService && filterService !== 'all') {
        params.append('service_id', filterService);
      }

      // Count params
      const countParams = new URLSearchParams();
      if (filterStatus && filterStatus !== 'all') {
        countParams.append('status', filterStatus);
      }
      if (filterDateFrom) {
        countParams.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        countParams.append('date_to', filterDateTo);
      }
      if (filterService && filterService !== 'all') {
        countParams.append('service_id', filterService);
      }
      
      const [jobsRes, countRes] = await Promise.all([
        axios.get(`${API}/jobs?${params.toString()}`),
        axios.get(`${API}/jobs/count/total${countParams.toString() ? '?' + countParams.toString() : ''}`)
      ]);
      setJobs(jobsRes.data);
      setTotalJobs(countRes.data.total);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  // NEW: Check if filters are active
  const hasActiveFilters = filterStatus !== 'all' || filterDateFrom || filterDateTo || filterService !== 'all';

  // NEW: Clear all filters
  const clearFilters = () => {
    setFilterStatus('all');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterService('all');
    setCurrentPage(1);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const fetchEmployees = async () => {
    try {
      const response = await axios.get(`${API}/authority/employees`);
      setEmployees(response.data);
    } catch (error) {
      console.error('Error fetching employees:', error);
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

  // Employee Management Functions
  const handleCreateEmployee = async (e) => {
    e.preventDefault();
    if (!newEmployeeName || !newEmployeeEmail || !newEmployeePassword) {
      toast.error('Bitte füllen Sie alle Felder aus');
      return;
    }

    setCreatingEmployee(true);
    try {
      await axios.post(`${API}/authority/employees`, {
        name: newEmployeeName,
        email: newEmployeeEmail,
        password: newEmployeePassword
      });
      toast.success('Mitarbeiter erfolgreich angelegt');
      setEmployeeDialogOpen(false);
      setNewEmployeeName('');
      setNewEmployeeEmail('');
      setNewEmployeePassword('');
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Anlegen');
    } finally {
      setCreatingEmployee(false);
    }
  };

  const handleBlockEmployee = async (employeeId, block) => {
    try {
      await axios.patch(`${API}/authority/employees/${employeeId}/block`, { blocked: block });
      toast.success(block ? 'Mitarbeiter gesperrt' : 'Mitarbeiter entsperrt');
      fetchEmployees();
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
  };

  const handleDeleteEmployee = async (employeeId) => {
    if (!window.confirm('Mitarbeiter wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
      return;
    }
    try {
      await axios.delete(`${API}/authority/employees/${employeeId}`);
      toast.success('Mitarbeiter gelöscht');
      fetchEmployees();
    } catch (error) {
      toast.error('Fehler beim Löschen');
    }
  };

  const handleChangeEmployeePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      toast.error('Passwort muss mindestens 6 Zeichen haben');
      return;
    }
    try {
      await axios.patch(`${API}/authority/employees/${selectedEmployee.id}/password`, {
        new_password: newPassword
      });
      toast.success('Passwort geändert');
      setPasswordDialogOpen(false);
      setNewPassword('');
      setSelectedEmployee(null);
    } catch (error) {
      toast.error('Fehler beim Ändern des Passworts');
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

    // Validate Sicherstellung fields
    if (jobType === 'sicherstellung' && !sicherstellungReason) {
      toast.error('Bitte wählen Sie einen Grund für die Sicherstellung');
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
        assigned_service_id: selectedServiceId || null,
        // NEW: Job type and Sicherstellung fields
        job_type: jobType,
        sicherstellung_reason: jobType === 'sicherstellung' ? sicherstellungReason : null,
        vehicle_category: jobType === 'sicherstellung' ? vehicleCategory : null,
        ordering_authority: jobType === 'sicherstellung' ? orderingAuthority : null,
        contact_attempts: jobType === 'sicherstellung' ? contactAttempts : null,
        contact_attempts_notes: jobType === 'sicherstellung' && contactAttempts ? contactAttemptsNotes : null,
        estimated_vehicle_value: jobType === 'sicherstellung' && estimatedVehicleValue ? parseFloat(estimatedVehicleValue) : null
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
      setJobType('towing');
      setSicherstellungReason('');
      setVehicleCategory('under_3_5t');
      setOrderingAuthority('');
      setContactAttempts(false);
      setContactAttemptsNotes('');
      setEstimatedVehicleValue('');
      
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
        {/* Dienstnummer Badge */}
        {user?.dienstnummer && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="py-3">
              <div className="flex items-center gap-3">
                <Badge className="h-5 w-5 text-blue-600" />
                <div>
                  <span className="text-sm text-blue-700">Ihre Dienstnummer: </span>
                  <span className="font-mono font-bold text-blue-900">{user.dienstnummer}</span>
                </div>
                {!user?.is_main_authority && (
                  <span className="text-xs text-blue-600 ml-2">(Mitarbeiter-Account)</span>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-new-job" value="new" className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Neuer Auftrag
            </TabsTrigger>
            <TabsTrigger data-testid="tab-my-jobs" value="jobs" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              {user?.is_main_authority ? 'Alle Aufträge' : 'Meine Aufträge'}
            </TabsTrigger>
            <TabsTrigger data-testid="tab-services" value="services" className="flex items-center gap-2">
              <LinkIcon className="h-4 w-4" />
              Abschleppdienste
            </TabsTrigger>
            {user?.is_main_authority && (
              <TabsTrigger data-testid="tab-employees" value="employees" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Mitarbeiter ({employees.length})
              </TabsTrigger>
            )}
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
                    {/* NEW: Job Type Selection */}
                    <div className="space-y-3">
                      <Label>Art des Auftrags *</Label>
                      <div className="flex gap-4">
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${jobType === 'towing' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="jobType"
                            value="towing"
                            checked={jobType === 'towing'}
                            onChange={(e) => setJobType(e.target.value)}
                            className="w-4 h-4"
                          />
                          <span className="font-medium">Abschleppen</span>
                          <span className="text-xs text-slate-500">(Falschparker)</span>
                        </label>
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${jobType === 'sicherstellung' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="jobType"
                            value="sicherstellung"
                            checked={jobType === 'sicherstellung'}
                            onChange={(e) => setJobType(e.target.value)}
                            className="w-4 h-4"
                          />
                          <span className="font-medium">Sicherstellung</span>
                          <span className="text-xs text-slate-500">(Polizeilich)</span>
                        </label>
                      </div>
                    </div>

                    {/* Sicherstellung-specific fields */}
                    {jobType === 'sicherstellung' && (
                      <div className="space-y-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                        <h4 className="font-semibold text-amber-800">Sicherstellungs-Details</h4>
                        
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Grund der Sicherstellung *</Label>
                            <Select value={sicherstellungReason} onValueChange={setSicherstellungReason}>
                              <SelectTrigger>
                                <SelectValue placeholder="Grund auswählen" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="betriebsmittel">Auslaufende Betriebsmittel</SelectItem>
                                <SelectItem value="gestohlen">Gestohlenes Fahrzeug / Fahndung</SelectItem>
                                <SelectItem value="eigentumssicherung">Eigentumssicherung (wertvoll/ungesichert)</SelectItem>
                                <SelectItem value="technische_maengel">Technische Mängel / Beweissicherung</SelectItem>
                                <SelectItem value="strafrechtlich">Strafrechtliche Beschlagnahme</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Fahrzeugkategorie</Label>
                            <Select value={vehicleCategory} onValueChange={setVehicleCategory}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="under_3_5t">PKW/Krad bis 3,5t</SelectItem>
                                <SelectItem value="over_3_5t">Fahrzeuge ab 3,5t</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Anordnende Stelle</Label>
                            <Select value={orderingAuthority} onValueChange={setOrderingAuthority}>
                              <SelectTrigger>
                                <SelectValue placeholder="Stelle auswählen" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="schutzpolizei">Schutzpolizei</SelectItem>
                                <SelectItem value="kriminalpolizei">Kriminalpolizei</SelectItem>
                                <SelectItem value="staatsanwaltschaft">Staatsanwaltschaft</SelectItem>
                                <SelectItem value="sachverstaendiger">Technischer Sachverständiger</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Geschätzter Fahrzeugwert (€)</Label>
                            <Input
                              type="number"
                              value={estimatedVehicleValue}
                              onChange={(e) => setEstimatedVehicleValue(e.target.value)}
                              placeholder="z.B. 15000"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id="contactAttempts"
                              checked={contactAttempts}
                              onChange={(e) => setContactAttempts(e.target.checked)}
                              className="w-4 h-4"
                            />
                            <Label htmlFor="contactAttempts" className="cursor-pointer">
                              Telefonische Kontaktversuche durchgeführt
                            </Label>
                          </div>
                          {contactAttempts && (
                            <Textarea
                              value={contactAttemptsNotes}
                              onChange={(e) => setContactAttemptsNotes(e.target.value)}
                              placeholder="Dokumentation der Kontaktversuche..."
                              rows={2}
                              className="mt-2"
                            />
                          )}
                        </div>
                      </div>
                    )}

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
                          <div className="flex items-center gap-2">
                            {job.created_by_dienstnummer && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-mono">
                                {job.created_by_dienstnummer}
                              </span>
                            )}
                            {getStatusBadge(job.status)}
                          </div>
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
                        <p className="mt-2 text-sm text-slate-600">
                          Erfasst von: <span className="font-medium">{job.created_by_name}</span>
                          {job.created_by_dienstnummer && (
                            <span className="text-slate-400 ml-1">({job.created_by_dienstnummer})</span>
                          )}
                        </p>
                        {job.assigned_service_name && (
                          <p className="text-sm text-slate-600">
                            Zugewiesen an: <span className="font-medium">{job.assigned_service_name}</span>
                          </p>
                        )}
                        
                        {/* Timeline / Zeiterfassung */}
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-xs font-semibold text-slate-500 mb-2">ZEITERFASSUNG</p>
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                            <div className={`p-2 rounded ${job.created_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Meldung</p>
                              <p className="text-slate-500">{job.created_at ? new Date(job.created_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            <div className={`p-2 rounded ${job.on_site_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Vor Ort</p>
                              <p className="text-slate-500">{job.on_site_at ? new Date(job.on_site_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            <div className={`p-2 rounded ${job.towed_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Abgeschleppt</p>
                              <p className="text-slate-500">{job.towed_at ? new Date(job.towed_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            <div className={`p-2 rounded ${job.in_yard_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Im Hof</p>
                              <p className="text-slate-500">{job.in_yard_at ? new Date(job.in_yard_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            <div className={`p-2 rounded ${job.released_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Abgeholt</p>
                              <p className="text-slate-500">{job.released_at ? new Date(job.released_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                          </div>
                        </div>
                        
                        {/* PDF Download Button - shows when job is released */}
                        {job.status === 'released' && (
                          <div className="mt-4 pt-4 border-t flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => window.open(`${API}/jobs/${job.id}/pdf`, '_blank')}
                              className="flex items-center gap-2"
                            >
                              <Download className="h-4 w-4" />
                              PDF herunterladen
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Pagination */}
                {!loading && jobs.length > 0 && (
                  <Pagination 
                    currentPage={currentPage}
                    totalPages={Math.ceil(totalJobs / itemsPerPage)}
                    totalItems={totalJobs}
                    itemsPerPage={itemsPerPage}
                    onPageChange={handlePageChange}
                  />
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

          {/* Employees Tab - Only for Main Authority */}
          {user?.is_main_authority && (
            <TabsContent value="employees">
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Mitarbeiter verwalten
                      </CardTitle>
                      <CardDescription>
                        Mitarbeiter können sich einloggen und Fahrzeuge erfassen
                      </CardDescription>
                    </div>
                    <Button onClick={() => setEmployeeDialogOpen(true)}>
                      <UserPlus className="h-4 w-4 mr-2" />
                      Neuer Mitarbeiter
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {employees.length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                      <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Noch keine Mitarbeiter angelegt</p>
                      <p className="text-sm">Legen Sie Mitarbeiter an, damit diese Fahrzeuge erfassen können</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {employees.map(emp => (
                        <div 
                          key={emp.id} 
                          className={`flex items-center justify-between p-4 border rounded-lg ${
                            emp.is_blocked ? 'bg-red-50 border-red-200' : 'bg-white'
                          }`}
                        >
                          <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                              emp.is_blocked ? 'bg-red-200' : 'bg-blue-100'
                            }`}>
                              <Users className={`h-5 w-5 ${emp.is_blocked ? 'text-red-600' : 'text-blue-600'}`} />
                            </div>
                            <div>
                              <p className="font-medium">{emp.name}</p>
                              <p className="text-sm text-slate-500">{emp.email}</p>
                            </div>
                            <div className="ml-4 px-3 py-1 bg-slate-100 rounded">
                              <span className="text-xs text-slate-500">Dienstnummer:</span>
                              <span className="ml-1 font-mono font-bold text-slate-700">{emp.dienstnummer}</span>
                            </div>
                            {emp.is_blocked && (
                              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded">Gesperrt</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedEmployee(emp);
                                setPasswordDialogOpen(true);
                              }}
                              title="Passwort ändern"
                            >
                              <Key className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleBlockEmployee(emp.id, !emp.is_blocked)}
                              title={emp.is_blocked ? 'Entsperren' : 'Sperren'}
                            >
                              {emp.is_blocked ? <Unlock className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteEmployee(emp.id)}
                              className="text-red-600 hover:text-red-700"
                              title="Löschen"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </main>

      {/* Create Employee Dialog */}
      <Dialog open={employeeDialogOpen} onOpenChange={setEmployeeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Neuen Mitarbeiter anlegen</DialogTitle>
            <DialogDescription>
              Der Mitarbeiter erhält automatisch eine Dienstnummer und kann sich einloggen
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateEmployee} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="empName">Name *</Label>
              <Input
                id="empName"
                value={newEmployeeName}
                onChange={(e) => setNewEmployeeName(e.target.value)}
                placeholder="Max Mustermann"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="empEmail">E-Mail *</Label>
              <Input
                id="empEmail"
                type="email"
                value={newEmployeeEmail}
                onChange={(e) => setNewEmployeeEmail(e.target.value)}
                placeholder="mitarbeiter@behoerde.de"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="empPassword">Passwort *</Label>
              <Input
                id="empPassword"
                type="password"
                value={newEmployeePassword}
                onChange={(e) => setNewEmployeePassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={creatingEmployee}>
              {creatingEmployee ? 'Wird angelegt...' : 'Mitarbeiter anlegen'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Change Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Passwort ändern</DialogTitle>
            <DialogDescription>
              Neues Passwort für {selectedEmployee?.name} setzen
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="newPwd">Neues Passwort</Label>
              <Input
                id="newPwd"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
              />
            </div>
            <Button onClick={handleChangeEmployeePassword} className="w-full">
              Passwort ändern
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AuthorityDashboard;
