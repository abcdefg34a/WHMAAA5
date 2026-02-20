import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { 
  Car, MapPin, Camera, LogOut, FileText, Copy, CheckCircle,
  Clock, Truck, Phone, Building2, Download, X
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
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

export const TowingDashboard = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('incoming');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetailOpen, setJobDetailOpen] = useState(false);
  const [releaseDialogOpen, setReleaseDialogOpen] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  // Release form state
  const [ownerFirstName, setOwnerFirstName] = useState('');
  const [ownerLastName, setOwnerLastName] = useState('');
  const [ownerAddress, setOwnerAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [serviceNotes, setServiceNotes] = useState('');
  const [servicePhotos, setServicePhotos] = useState([]);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchJobs();
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

  const copyServiceCode = () => {
    if (user?.service_code) {
      navigator.clipboard.writeText(user.service_code);
      setCodeCopied(true);
      toast.success('Code kopiert!');
      setTimeout(() => setCodeCopied(false), 2000);
    }
  };

  const handleStatusUpdate = async (jobId, newStatus) => {
    try {
      const updateData = { status: newStatus };
      if (serviceNotes) updateData.service_notes = serviceNotes;
      
      await axios.patch(`${API}/jobs/${jobId}`, updateData);
      toast.success('Status aktualisiert');
      fetchJobs();
      
      if (selectedJob?.id === jobId) {
        const response = await axios.get(`${API}/jobs/${jobId}`);
        setSelectedJob(response.data);
      }
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
  };

  const handleReleaseVehicle = async () => {
    if (!selectedJob) return;
    
    if (!ownerFirstName || !ownerLastName || !paymentAmount) {
      toast.error('Bitte füllen Sie alle Pflichtfelder aus');
      return;
    }

    try {
      await axios.patch(`${API}/jobs/${selectedJob.id}`, {
        status: 'released',
        owner_first_name: ownerFirstName,
        owner_last_name: ownerLastName,
        owner_address: ownerAddress,
        payment_method: paymentMethod,
        payment_amount: parseFloat(paymentAmount)
      });
      
      toast.success('Fahrzeug als abgeholt markiert');
      setReleaseDialogOpen(false);
      setJobDetailOpen(false);
      resetReleaseForm();
      fetchJobs();
      
      // Download PDF
      window.open(`${API}/jobs/${selectedJob.id}/pdf`, '_blank');
    } catch (error) {
      toast.error('Fehler bei der Freigabe');
    }
  };

  const resetReleaseForm = () => {
    setOwnerFirstName('');
    setOwnerLastName('');
    setOwnerAddress('');
    setPaymentMethod('cash');
    setPaymentAmount('');
  };

  const handlePhotoUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setServicePhotos(prev => [...prev, e.target.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const openJobDetail = (job) => {
    setSelectedJob(job);
    setServiceNotes(job.service_notes || '');
    setJobDetailOpen(true);
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

  const filterJobs = (status) => {
    if (status === 'incoming') {
      return jobs.filter(j => ['assigned', 'on_site', 'towed'].includes(j.status));
    }
    if (status === 'in_yard') {
      return jobs.filter(j => j.status === 'in_yard');
    }
    if (status === 'released') {
      return jobs.filter(j => j.status === 'released');
    }
    return jobs;
  };

  const downloadPDF = async (jobId) => {
    window.open(`${API}/jobs/${jobId}/pdf`, '_blank');
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Truck className="h-8 w-8 text-slate-900" />
              <div className="hidden sm:block">
                <h1 className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Abschleppdienst
                </h1>
                <p className="text-xs text-slate-500">{user?.company_name}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Service Code */}
              <div 
                className="hidden md:flex items-center gap-2 bg-slate-100 px-3 py-2 rounded-lg cursor-pointer"
                onClick={copyServiceCode}
              >
                <span className="text-xs text-slate-500">Ihr Code:</span>
                <span className="font-mono font-bold text-slate-900">{user?.service_code}</span>
                {codeCopied ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4 text-slate-400" />
                )}
              </div>
              
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
        {/* Service Code Card (Mobile) */}
        <Card className="mb-6 md:hidden">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Ihr Verknüpfungscode</p>
                <p className="font-mono font-bold text-2xl text-slate-900">{user?.service_code}</p>
              </div>
              <Button variant="outline" onClick={copyServiceCode}>
                {codeCopied ? <CheckCircle className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
              </Button>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Geben Sie diesen Code an Behörden weiter, um Aufträge zu erhalten
            </p>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-incoming" value="incoming" className="flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Eingehend ({filterJobs('incoming').length})
            </TabsTrigger>
            <TabsTrigger data-testid="tab-in-yard" value="in_yard" className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Im Hof ({filterJobs('in_yard').length})
            </TabsTrigger>
            <TabsTrigger data-testid="tab-released" value="released" className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Abgeholt ({filterJobs('released').length})
            </TabsTrigger>
          </TabsList>

          {/* Incoming Jobs */}
          <TabsContent value="incoming">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : filterJobs('incoming').length === 0 ? (
              <div className="empty-state">
                <Truck className="empty-state-icon" />
                <p>Keine eingehenden Aufträge</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filterJobs('incoming').map(job => (
                  <Card 
                    key={job.id} 
                    className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => openJobDetail(job)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <p className="job-license-plate">{job.license_plate}</p>
                          <p className="text-xs text-slate-500">{job.job_number}</p>
                        </div>
                        {getStatusBadge(job.status)}
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-slate-600">
                          <MapPin className="h-4 w-4 flex-shrink-0" />
                          <span className="truncate">{job.location_address}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-600">
                          <Clock className="h-4 w-4" />
                          <span>{new Date(job.created_at).toLocaleString('de-DE')}</span>
                        </div>
                      </div>
                      <p className="mt-2 text-sm font-medium text-orange-600">
                        {job.tow_reason}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* In Yard */}
          <TabsContent value="in_yard">
            {filterJobs('in_yard').length === 0 ? (
              <div className="empty-state">
                <Building2 className="empty-state-icon" />
                <p>Keine Fahrzeuge im Hof</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filterJobs('in_yard').map(job => (
                  <Card 
                    key={job.id} 
                    className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => openJobDetail(job)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <p className="job-license-plate">{job.license_plate}</p>
                          <p className="text-xs text-slate-500">{job.job_number}</p>
                        </div>
                        {getStatusBadge(job.status)}
                      </div>
                      <div className="space-y-2 text-sm text-slate-600">
                        <p>Im Hof seit: {job.in_yard_at ? new Date(job.in_yard_at).toLocaleString('de-DE') : '-'}</p>
                        {job.vin && <p>FIN: {job.vin}</p>}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Released */}
          <TabsContent value="released">
            {filterJobs('released').length === 0 ? (
              <div className="empty-state">
                <CheckCircle className="empty-state-icon" />
                <p>Keine abgeholten Fahrzeuge</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filterJobs('released').map(job => (
                  <Card key={job.id}>
                    <CardContent className="p-4">
                      <div className="flex flex-wrap justify-between items-start gap-4">
                        <div>
                          <p className="job-license-plate">{job.license_plate}</p>
                          <p className="text-xs text-slate-500">{job.job_number}</p>
                          <p className="text-sm text-slate-600 mt-1">
                            Abgeholt von: {job.owner_first_name} {job.owner_last_name}
                          </p>
                          <p className="text-sm text-slate-600">
                            Zahlung: {job.payment_amount?.toFixed(2)} € ({job.payment_method === 'cash' ? 'Bar' : 'Karte'})
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          onClick={() => downloadPDF(job.id)}
                          className="flex items-center gap-2"
                        >
                          <Download className="h-4 w-4" />
                          PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Job Detail Dialog */}
      <Dialog open={jobDetailOpen} onOpenChange={setJobDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <span className="job-license-plate text-2xl">{selectedJob.license_plate}</span>
                  {getStatusBadge(selectedJob.status)}
                </DialogTitle>
                <DialogDescription>
                  {selectedJob.job_number} • {selectedJob.tow_reason}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {/* Location Map */}
                <div className="map-container h-48">
                  <MapContainer
                    center={[selectedJob.location_lat, selectedJob.location_lng]}
                    zoom={15}
                    scrollWheelZoom={false}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[selectedJob.location_lat, selectedJob.location_lng]}>
                      <Popup>{selectedJob.location_address}</Popup>
                    </Marker>
                  </MapContainer>
                </div>

                {/* Vehicle Details */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-slate-500">Kennzeichen</Label>
                    <p className="font-bold">{selectedJob.license_plate}</p>
                  </div>
                  {selectedJob.vin && (
                    <div>
                      <Label className="text-slate-500">FIN</Label>
                      <p className="font-mono">{selectedJob.vin}</p>
                    </div>
                  )}
                  <div>
                    <Label className="text-slate-500">Erfasst von</Label>
                    <p>{selectedJob.created_by_name}</p>
                    <p className="text-sm text-slate-500">{selectedJob.created_by_authority}</p>
                  </div>
                  <div>
                    <Label className="text-slate-500">Erfasst am</Label>
                    <p>{new Date(selectedJob.created_at).toLocaleString('de-DE')}</p>
                  </div>
                </div>

                {/* Photos */}
                {selectedJob.photos && selectedJob.photos.length > 0 && (
                  <div>
                    <Label className="text-slate-500 mb-2 block">Fotos</Label>
                    <div className="photo-grid">
                      {selectedJob.photos.map((photo, idx) => (
                        <img key={idx} src={photo} alt={`Foto ${idx + 1}`} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes */}
                <div>
                  <Label htmlFor="serviceNotes" className="text-slate-500">Eigene Bemerkungen</Label>
                  <Textarea
                    id="serviceNotes"
                    value={serviceNotes}
                    onChange={(e) => setServiceNotes(e.target.value)}
                    placeholder="Beschreibung oder Anmerkungen hinzufügen..."
                    rows={2}
                    className="mt-1"
                  />
                </div>

                {/* Add Photo */}
                <div>
                  <Label className="text-slate-500 mb-2 block">Foto hinzufügen</Label>
                  <div className="flex gap-2">
                    {servicePhotos.map((photo, idx) => (
                      <div key={idx} className="relative w-16 h-16">
                        <img src={photo} alt="" className="w-full h-full object-cover rounded" />
                        <button
                          onClick={() => setServicePhotos(prev => prev.filter((_, i) => i !== idx))}
                          className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-16 h-16 border-2 border-dashed border-slate-300 rounded flex items-center justify-center hover:border-slate-400"
                    >
                      <Camera className="h-5 w-5 text-slate-400" />
                    </button>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handlePhotoUpload}
                    className="hidden"
                  />
                </div>

                {/* Status Actions */}
                <div className="border-t pt-4">
                  <Label className="text-slate-500 mb-3 block">Status aktualisieren</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.status === 'assigned' && (
                      <Button
                        data-testid="status-on-site-btn"
                        onClick={() => handleStatusUpdate(selectedJob.id, 'on_site')}
                        className="bg-orange-500 hover:bg-orange-600"
                      >
                        <MapPin className="h-4 w-4 mr-2" />
                        Bin vor Ort
                      </Button>
                    )}
                    {selectedJob.status === 'on_site' && (
                      <Button
                        data-testid="status-towed-btn"
                        onClick={() => handleStatusUpdate(selectedJob.id, 'towed')}
                        className="bg-red-500 hover:bg-red-600"
                      >
                        <Truck className="h-4 w-4 mr-2" />
                        Abgeschleppt
                      </Button>
                    )}
                    {selectedJob.status === 'towed' && (
                      <Button
                        data-testid="status-in-yard-btn"
                        onClick={() => handleStatusUpdate(selectedJob.id, 'in_yard')}
                        className="bg-yellow-500 hover:bg-yellow-600"
                      >
                        <Building2 className="h-4 w-4 mr-2" />
                        Im Hof angekommen
                      </Button>
                    )}
                    {selectedJob.status === 'in_yard' && (
                      <Button
                        data-testid="status-release-btn"
                        onClick={() => setReleaseDialogOpen(true)}
                        className="bg-green-500 hover:bg-green-600"
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Fahrzeug freigeben
                      </Button>
                    )}
                  </div>
                </div>

                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${selectedJob.location_lat},${selectedJob.location_lng}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-orange-600 hover:text-orange-700"
                >
                  <MapPin className="h-4 w-4" />
                  Navigation starten
                </a>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Release Dialog */}
      <Dialog open={releaseDialogOpen} onOpenChange={setReleaseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Fahrzeug freigeben</DialogTitle>
            <DialogDescription>
              Geben Sie die Daten des Halters und die Zahlungsinformationen ein
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ownerFirstName">Vorname *</Label>
                <Input
                  data-testid="release-firstname-input"
                  id="ownerFirstName"
                  value={ownerFirstName}
                  onChange={(e) => setOwnerFirstName(e.target.value)}
                  placeholder="Max"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ownerLastName">Nachname *</Label>
                <Input
                  data-testid="release-lastname-input"
                  id="ownerLastName"
                  value={ownerLastName}
                  onChange={(e) => setOwnerLastName(e.target.value)}
                  placeholder="Mustermann"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ownerAddress">Adresse</Label>
              <Input
                data-testid="release-address-input"
                id="ownerAddress"
                value={ownerAddress}
                onChange={(e) => setOwnerAddress(e.target.value)}
                placeholder="Musterstraße 1, 12345 Berlin"
              />
            </div>

            <div className="space-y-2">
              <Label>Zahlungsart *</Label>
              <RadioGroup value={paymentMethod} onValueChange={setPaymentMethod}>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="cash" id="cash" />
                    <Label htmlFor="cash">Bar</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="card" id="card" />
                    <Label htmlFor="card">Karte</Label>
                  </div>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-2">
              <Label htmlFor="paymentAmount">Betrag (€) *</Label>
              <Input
                data-testid="release-amount-input"
                id="paymentAmount"
                type="number"
                step="0.01"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder="250.00"
                required
              />
            </div>

            <Button
              data-testid="confirm-release-btn"
              onClick={handleReleaseVehicle}
              className="w-full bg-green-600 hover:bg-green-700"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Freigabe bestätigen & PDF erstellen
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TowingDashboard;
