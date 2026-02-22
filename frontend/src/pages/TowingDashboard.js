import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { 
  Car, MapPin, Camera, LogOut, FileText, Copy, CheckCircle,
  Clock, Truck, Phone, Building2, Download, X, Settings, Euro,
  Filter, CheckSquare, Square, ChevronDown, Calendar, Plus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
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

// Location Picker Component for Map
const LocationPicker = ({ position, setPosition }) => {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });

  return position ? <Marker position={position} /> : null;
};

export const TowingDashboard = () => {
  const { user, logout, updateUser } = useAuth();
  const [activeTab, setActiveTab] = useState('incoming');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetailOpen, setJobDetailOpen] = useState(false);
  const [releaseDialogOpen, setReleaseDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  // Bulk selection state
  const [selectedJobIds, setSelectedJobIds] = useState([]);
  const [bulkUpdating, setBulkUpdating] = useState(false);

  // Filter state
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const itemsPerPage = 50;

  // Release form state
  const [ownerFirstName, setOwnerFirstName] = useState('');
  const [ownerLastName, setOwnerLastName] = useState('');
  const [ownerAddress, setOwnerAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [serviceNotes, setServiceNotes] = useState('');
  const [servicePhotos, setServicePhotos] = useState([]);
  const fileInputRef = useRef(null);

  // Settings state (costs)
  const [towCost, setTowCost] = useState(user?.tow_cost || 0);
  const [dailyCost, setDailyCost] = useState(user?.daily_cost || 0);
  const [savingCosts, setSavingCosts] = useState(false);

  // NEW: Extended pricing settings
  const [timeBasedEnabled, setTimeBasedEnabled] = useState(user?.time_based_enabled || false);
  const [firstHalfHour, setFirstHalfHour] = useState(user?.first_half_hour || '');
  const [additionalHalfHour, setAdditionalHalfHour] = useState(user?.additional_half_hour || '');
  const [processingFee, setProcessingFee] = useState(user?.processing_fee || '');
  const [emptyTripFee, setEmptyTripFee] = useState(user?.empty_trip_fee || '');
  const [nightSurcharge, setNightSurcharge] = useState(user?.night_surcharge || '');
  const [weekendSurcharge, setWeekendSurcharge] = useState(user?.weekend_surcharge || '');
  const [heavyVehicleSurcharge, setHeavyVehicleSurcharge] = useState(user?.heavy_vehicle_surcharge || '');

  // Cost calculation state
  const [calculatedCosts, setCalculatedCosts] = useState(null);
  const [loadingCosts, setLoadingCosts] = useState(false);

  // NEW: Create Job state
  const [createJobDialogOpen, setCreateJobDialogOpen] = useState(false);
  const [linkedAuthorities, setLinkedAuthorities] = useState([]);
  const [loadingAuthorities, setLoadingAuthorities] = useState(false);
  const [creatingJob, setCreatingJob] = useState(false);
  const [newJobPosition, setNewJobPosition] = useState(null); // Map position
  const [newJobData, setNewJobData] = useState({
    for_authority_id: '',
    license_plate: '',
    vin: '',
    tow_reason: '',
    location_address: '',
    location_lat: 52.52,
    location_lng: 13.405,
    notes: '',
    job_type: 'towing',
    // Sicherstellung fields
    sicherstellung_reason: '',
    vehicle_category: 'under_3_5t',
    ordering_authority: '',
    contact_attempts: false,
    contact_attempts_notes: '',
    estimated_vehicle_value: ''
  });
  const [newJobPhotos, setNewJobPhotos] = useState([]);
  const newJobFileInputRef = useRef(null);

  useEffect(() => {
    fetchJobs();
  }, [filterStatus, filterDateFrom, filterDateTo, currentPage]);

  useEffect(() => {
    setTowCost(user?.tow_cost || 0);
    setDailyCost(user?.daily_cost || 0);
    setTimeBasedEnabled(user?.time_based_enabled || false);
    setFirstHalfHour(user?.first_half_hour || '');
    setAdditionalHalfHour(user?.additional_half_hour || '');
    setProcessingFee(user?.processing_fee || '');
    setEmptyTripFee(user?.empty_trip_fee || '');
    setNightSurcharge(user?.night_surcharge || '');
    setWeekendSurcharge(user?.weekend_surcharge || '');
    setHeavyVehicleSurcharge(user?.heavy_vehicle_surcharge || '');
  }, [user]);

  // Clear selection when tab changes
  useEffect(() => {
    setSelectedJobIds([]);
  }, [activeTab]);

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());
      if (filterStatus && filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterDateFrom) {
        params.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        params.append('date_to', filterDateTo);
      }
      
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
      
      const [jobsRes, countRes] = await Promise.all([
        axios.get(`${API}/jobs?${params.toString()}`),
        axios.get(`${API}/jobs/count/total?${countParams.toString()}`)
      ]);
      setJobs(jobsRes.data);
      setTotalJobs(countRes.data.total);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  // Bulk selection handlers
  const toggleJobSelection = (jobId, event) => {
    event.stopPropagation();
    setSelectedJobIds(prev => 
      prev.includes(jobId) 
        ? prev.filter(id => id !== jobId)
        : [...prev, jobId]
    );
  };

  const selectAllInTab = (tabJobs) => {
    const tabJobIds = tabJobs.map(j => j.id);
    const allSelected = tabJobIds.every(id => selectedJobIds.includes(id));
    if (allSelected) {
      setSelectedJobIds(prev => prev.filter(id => !tabJobIds.includes(id)));
    } else {
      setSelectedJobIds(prev => [...new Set([...prev, ...tabJobIds])]);
    }
  };

  const handleBulkStatusUpdate = async (newStatus) => {
    if (selectedJobIds.length === 0) return;
    
    setBulkUpdating(true);
    try {
      const response = await axios.post(`${API}/jobs/bulk-update-status`, {
        job_ids: selectedJobIds,
        status: newStatus
      });
      toast.success(response.data.message);
      setSelectedJobIds([]);
      fetchJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler bei der Massenaktualisierung');
    } finally {
      setBulkUpdating(false);
    }
  };

  const clearFilters = () => {
    setFilterStatus('all');
    setFilterDateFrom('');
    setFilterDateTo('');
    setCurrentPage(1);
  };

  const hasActiveFilters = filterStatus !== 'all' || filterDateFrom || filterDateTo;

  // NEW: Fetch linked authorities for job creation
  const fetchLinkedAuthorities = async () => {
    setLoadingAuthorities(true);
    try {
      const response = await axios.get(`${API}/towing/linked-authorities`);
      setLinkedAuthorities(response.data);
    } catch (error) {
      console.error('Error fetching linked authorities:', error);
      toast.error('Fehler beim Laden der verknüpften Behörden');
    } finally {
      setLoadingAuthorities(false);
    }
  };

  // NEW: Open create job dialog
  const openCreateJobDialog = () => {
    fetchLinkedAuthorities();
    setNewJobData({
      for_authority_id: '',
      license_plate: '',
      vin: '',
      tow_reason: '',
      location_address: '',
      location_lat: 52.52,
      location_lng: 13.405,
      notes: '',
      job_type: 'towing',
      sicherstellung_reason: '',
      vehicle_category: 'under_3_5t',
      ordering_authority: '',
      contact_attempts: false,
      contact_attempts_notes: '',
      estimated_vehicle_value: ''
    });
    setNewJobPhotos([]);
    setNewJobPosition(null);
    setCreateJobDialogOpen(true);
  };

  // NEW: Get current location for new job
  const handleGetNewJobLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const newPos = [pos.coords.latitude, pos.coords.longitude];
          setNewJobPosition(newPos);
          setNewJobData(prev => ({
            ...prev,
            location_lat: pos.coords.latitude,
            location_lng: pos.coords.longitude,
            location_address: `${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}`
          }));
          toast.success('Standort erfasst!');
        },
        (error) => {
          toast.error('Standort konnte nicht ermittelt werden');
        }
      );
    } else {
      toast.error('Geolocation wird nicht unterstützt');
    }
  };

  // NEW: Handle map click for new job
  const handleNewJobMapClick = (pos) => {
    setNewJobPosition(pos);
    setNewJobData(prev => ({
      ...prev,
      location_lat: pos[0],
      location_lng: pos[1],
      location_address: `${pos[0].toFixed(6)}, ${pos[1].toFixed(6)}`
    }));
  };

  // NEW: Handle new job photo upload
  const handleNewJobPhotoUpload = (e) => {
    const files = Array.from(e.target.files);
    if (newJobPhotos.length + files.length > 5) {
      toast.error('Maximal 5 Fotos erlaubt');
      return;
    }
    files.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setNewJobPhotos(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  // NEW: Remove photo from new job
  const removeNewJobPhoto = (index) => {
    setNewJobPhotos(prev => prev.filter((_, i) => i !== index));
  };

  // NEW: Create job as towing service
  const handleCreateJob = async () => {
    // Validation
    if (!newJobData.for_authority_id) {
      toast.error('Bitte wählen Sie eine Behörde aus');
      return;
    }
    if (!newJobData.license_plate) {
      toast.error('Bitte geben Sie ein Kennzeichen ein');
      return;
    }
    if (!newJobData.tow_reason) {
      toast.error('Bitte geben Sie einen Abschleppgrund ein');
      return;
    }
    if (!newJobData.location_address) {
      toast.error('Bitte geben Sie eine Adresse ein');
      return;
    }

    setCreatingJob(true);
    try {
      const payload = {
        ...newJobData,
        photos: newJobPhotos,
        estimated_vehicle_value: newJobData.estimated_vehicle_value ? parseFloat(newJobData.estimated_vehicle_value) : null
      };

      await axios.post(`${API}/jobs`, payload);
      toast.success('Auftrag erfolgreich erstellt!');
      setCreateJobDialogOpen(false);
      fetchJobs();
    } catch (error) {
      console.error('Error creating job:', error);
      toast.error(error.response?.data?.detail || 'Fehler beim Erstellen des Auftrags');
    } finally {
      setCreatingJob(false);
    }
  };

  const copyServiceCode = async () => {
    if (user?.service_code) {
      try {
        await navigator.clipboard.writeText(user.service_code);
        setCodeCopied(true);
        toast.success('Code kopiert!');
        setTimeout(() => setCodeCopied(false), 2000);
      } catch (err) {
        // Fallback for browsers that don't support clipboard
        toast.info(`Ihr Code: ${user.service_code}`);
      }
    }
  };

  const handleSaveCosts = async () => {
    setSavingCosts(true);
    try {
      const response = await axios.patch(`${API}/services/pricing-settings`, {
        time_based_enabled: timeBasedEnabled,
        first_half_hour: parseFloat(firstHalfHour) || null,
        additional_half_hour: parseFloat(additionalHalfHour) || null,
        tow_cost: parseFloat(towCost) || null,
        daily_cost: parseFloat(dailyCost) || null,
        processing_fee: parseFloat(processingFee) || null,
        empty_trip_fee: parseFloat(emptyTripFee) || null,
        night_surcharge: parseFloat(nightSurcharge) || null,
        weekend_surcharge: parseFloat(weekendSurcharge) || null,
        heavy_vehicle_surcharge: parseFloat(heavyVehicleSurcharge) || null
      });
      updateUser(response.data);
      toast.success('Preiseinstellungen gespeichert!');
      setSettingsDialogOpen(false);
    } catch (error) {
      toast.error('Fehler beim Speichern');
    } finally {
      setSavingCosts(false);
    }
  };

  const fetchCalculatedCosts = async (jobId) => {
    setLoadingCosts(true);
    try {
      const response = await axios.get(`${API}/jobs/${jobId}/calculate-costs`);
      setCalculatedCosts(response.data);
      if (response.data.total > 0) {
        setPaymentAmount(response.data.total.toString());
      }
    } catch (error) {
      console.error('Error calculating costs:', error);
    } finally {
      setLoadingCosts(false);
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

  const getStatusBadge = (status, isEmptyTrip = false) => {
    if (isEmptyTrip) {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          Leerfahrt
        </span>
      );
    }
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

              {/* Settings Button */}
              <Button
                data-testid="settings-btn"
                variant="outline"
                size="sm"
                onClick={() => setSettingsDialogOpen(true)}
              >
                <Settings className="h-4 w-4" />
              </Button>
              
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

        {/* Cost Info Card */}
        <Card className="mb-6 border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Euro className="h-6 w-6 text-orange-600" />
                <div>
                  <p className="text-sm text-orange-700">Ihre Preise</p>
                  <p className="font-bold text-orange-900">
                    Anfahrt: {(user?.tow_cost || 0).toFixed(2)} € | Standkosten: {(user?.daily_cost || 0).toFixed(2)} €/Tag
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={() => setSettingsDialogOpen(true)}>
                Anpassen
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* NEW: Create Job Card */}
        <Card className="mb-6 border-green-200 bg-green-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Car className="h-6 w-6 text-green-600" />
                <div>
                  <p className="text-sm text-green-700">Eigenen Auftrag erstellen</p>
                  <p className="font-bold text-green-900">
                    Erstellen Sie selbst einen Auftrag für eine verknüpfte Behörde
                  </p>
                </div>
              </div>
              <Button 
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={openCreateJobDialog}
              >
                + Neuer Auftrag
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Filter Section */}
        <Card className="mb-6">
          <CardContent className="py-4">
            <div className="flex flex-wrap items-center gap-4">
              <Button
                variant={filterOpen ? "default" : "outline"}
                size="sm"
                onClick={() => setFilterOpen(!filterOpen)}
                className="flex items-center gap-2"
              >
                <Filter className="h-4 w-4" />
                Filter
                {hasActiveFilters && (
                  <span className="bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded-full">!</span>
                )}
              </Button>
              
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  Filter zurücksetzen
                </Button>
              )}
            </div>

            {filterOpen && (
              <div className="mt-4 pt-4 border-t grid sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm text-slate-500">Status</Label>
                  <Select value={filterStatus} onValueChange={setFilterStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Alle Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Alle Status</SelectItem>
                      <SelectItem value="assigned">Zugewiesen</SelectItem>
                      <SelectItem value="on_site">Vor Ort</SelectItem>
                      <SelectItem value="towed">Abgeschleppt</SelectItem>
                      <SelectItem value="in_yard">Im Hof</SelectItem>
                      <SelectItem value="released">Abgeholt</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-slate-500">Datum von</Label>
                  <Input
                    type="date"
                    value={filterDateFrom}
                    onChange={(e) => setFilterDateFrom(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-slate-500">Datum bis</Label>
                  <Input
                    type="date"
                    value={filterDateTo}
                    onChange={(e) => setFilterDateTo(e.target.value)}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Bulk Action Bar - appears when items selected */}
        {selectedJobIds.length > 0 && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <CheckSquare className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-800">
                    {selectedJobIds.length} Auftrag{selectedJobIds.length > 1 ? 'e' : ''} ausgewählt
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-blue-700 mr-2">Status ändern:</span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('on_site')}
                    className="bg-orange-100 border-orange-300 text-orange-700 hover:bg-orange-200"
                  >
                    Vor Ort
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('towed')}
                    className="bg-red-100 border-red-300 text-red-700 hover:bg-red-200"
                  >
                    Abgeschleppt
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('in_yard')}
                    className="bg-yellow-100 border-yellow-300 text-yellow-700 hover:bg-yellow-200"
                  >
                    Im Hof
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setSelectedJobIds([])}
                    className="text-slate-500"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
              <>
                {/* Select All for Incoming */}
                <div className="mb-4 flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => selectAllInTab(filterJobs('incoming'))}
                    className="text-slate-600"
                  >
                    {filterJobs('incoming').every(j => selectedJobIds.includes(j.id)) ? (
                      <><CheckSquare className="h-4 w-4 mr-2" /> Alle abwählen</>
                    ) : (
                      <><Square className="h-4 w-4 mr-2" /> Alle auswählen</>
                    )}
                  </Button>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filterJobs('incoming').map(job => (
                    <Card 
                      key={job.id} 
                      className={`cursor-pointer hover:shadow-lg transition-shadow relative ${
                        selectedJobIds.includes(job.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => openJobDetail(job)}
                  >
                    {/* Checkbox */}
                    <button
                      className="absolute top-2 right-2 z-10 p-1 rounded hover:bg-slate-100"
                      onClick={(e) => toggleJobSelection(job.id, e)}
                    >
                      {selectedJobIds.includes(job.id) ? (
                        <CheckSquare className="h-5 w-5 text-blue-600" />
                      ) : (
                        <Square className="h-5 w-5 text-slate-400" />
                      )}
                    </button>
                    <CardContent className="p-4 pr-10">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <p className="job-license-plate">{job.license_plate}</p>
                          <p className="text-xs text-slate-500">{job.job_number}</p>
                        </div>
                        {getStatusBadge(job.status, job.is_empty_trip)}
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
                      {/* Show job type and sicherstellung details */}
                      {job.job_type === 'sicherstellung' && (
                        <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs">
                          <span className="font-semibold text-amber-800">Sicherstellung</span>
                          {job.sicherstellung_reason && (
                            <span className="text-amber-700"> • {
                              {
                                'betriebsmittel': 'Betriebsmittel',
                                'gestohlen': 'Gestohlen/Fahndung',
                                'eigentumssicherung': 'Eigentumssicherung',
                                'technische_maengel': 'Techn. Mängel',
                                'strafrechtlich': 'Strafrechtlich'
                              }[job.sicherstellung_reason] || job.sicherstellung_reason
                            }</span>
                          )}
                          {job.vehicle_category === 'over_3_5t' && (
                            <span className="text-amber-700"> • ab 3,5t</span>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
              </>
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
              <>
                {/* Select All for In Yard */}
                <div className="mb-4 flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => selectAllInTab(filterJobs('in_yard'))}
                    className="text-slate-600"
                  >
                    {filterJobs('in_yard').every(j => selectedJobIds.includes(j.id)) ? (
                      <><CheckSquare className="h-4 w-4 mr-2" /> Alle abwählen</>
                    ) : (
                      <><Square className="h-4 w-4 mr-2" /> Alle auswählen</>
                    )}
                  </Button>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filterJobs('in_yard').map(job => (
                    <Card 
                      key={job.id} 
                      className={`cursor-pointer hover:shadow-lg transition-shadow relative ${
                        selectedJobIds.includes(job.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => openJobDetail(job)}
                    >
                      {/* Checkbox */}
                      <button
                        className="absolute top-2 right-2 z-10 p-1 rounded hover:bg-slate-100"
                        onClick={(e) => toggleJobSelection(job.id, e)}
                      >
                        {selectedJobIds.includes(job.id) ? (
                          <CheckSquare className="h-5 w-5 text-blue-600" />
                        ) : (
                          <Square className="h-5 w-5 text-slate-400" />
                        )}
                      </button>
                      <CardContent className="p-4 pr-10">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <p className="job-license-plate">{job.license_plate}</p>
                            <p className="text-xs text-slate-500">{job.job_number}</p>
                          </div>
                          {getStatusBadge(job.status, job.is_empty_trip)}
                        </div>
                        <div className="space-y-2 text-sm text-slate-600">
                          <p>Im Hof seit: {job.in_yard_at ? new Date(job.in_yard_at).toLocaleString('de-DE') : '-'}</p>
                          {job.vin && <p>FIN: {job.vin}</p>}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
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
      </main>

      {/* Settings Dialog (Costs) */}
      <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Euro className="h-5 w-5" />
              Preiseinstellungen
            </DialogTitle>
            <DialogDescription>
              Konfigurieren Sie Ihre Preise - nur ausgefüllte Felder werden berechnet
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Zeitbasierte Berechnung */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold">Zeitbasierte Berechnung</h4>
                  <p className="text-xs text-slate-500">Für Sicherstellungen nach Berliner Gebührenordnung</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={timeBasedEnabled}
                    onChange={(e) => setTimeBasedEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              
              {timeBasedEnabled && (
                <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                  <div className="space-y-2">
                    <Label>Erste halbe Stunde (€)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={firstHalfHour}
                      onChange={(e) => setFirstHalfHour(e.target.value)}
                      placeholder="137.00"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Jede weitere halbe Stunde (€)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={additionalHalfHour}
                      onChange={(e) => setAdditionalHalfHour(e.target.value)}
                      placeholder="93.00"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Standard Preise */}
            <div className="space-y-4">
              <h4 className="font-semibold">Standard Preise</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Anfahrt/Abschleppen (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={towCost}
                    onChange={(e) => setTowCost(e.target.value)}
                    placeholder="150.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Standkosten pro Tag (€)</Label>
                  <Input
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

            {/* Zusatzkosten */}
            <div className="space-y-4">
              <h4 className="font-semibold">Zusatzkosten (optional)</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Bearbeitungsgebühr (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={processingFee}
                    onChange={(e) => setProcessingFee(e.target.value)}
                    placeholder="63.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Leerfahrt (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={emptyTripFee}
                    onChange={(e) => setEmptyTripFee(e.target.value)}
                    placeholder="31.50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nachtzuschlag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={nightSurcharge}
                    onChange={(e) => setNightSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-slate-500">22:00 - 06:00 Uhr</p>
                </div>
                <div className="space-y-2">
                  <Label>Wochenendzuschlag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={weekendSurcharge}
                    onChange={(e) => setWeekendSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-slate-500">Samstag & Sonntag</p>
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Schwerlastzuschlag ab 3,5t (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={heavyVehicleSurcharge}
                    onChange={(e) => setHeavyVehicleSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              </div>
            </div>

            {/* Beispielrechnung */}
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-sm font-medium text-slate-700">Beispielrechnung (Standard)</p>
              <p className="text-sm text-slate-600 mt-1">
                Fahrzeug 3 Tage im Hof: {parseFloat(towCost || 0).toFixed(2)} € + (3 × {parseFloat(dailyCost || 0).toFixed(2)} €) 
                {processingFee ? ` + ${parseFloat(processingFee).toFixed(2)} € Bearbeitung` : ''} 
                = <span className="font-bold">{(parseFloat(towCost || 0) + 3 * parseFloat(dailyCost || 0) + parseFloat(processingFee || 0)).toFixed(2)} €</span>
              </p>
            </div>

            <Button
              data-testid="save-costs-btn"
              onClick={handleSaveCosts}
              disabled={savingCosts}
              className="w-full bg-slate-900 hover:bg-slate-800"
            >
              {savingCosts ? <div className="loading-spinner mr-2"></div> : null}
              Speichern
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Job Detail Dialog */}
      <Dialog open={jobDetailOpen} onOpenChange={setJobDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <span className="job-license-plate text-2xl">{selectedJob.license_plate}</span>
                  {getStatusBadge(selectedJob.status, selectedJob.is_empty_trip)}
                </DialogTitle>
                <DialogDescription>
                  {selectedJob.job_number} • {selectedJob.tow_reason}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {/* Sicherstellung Details - prominent display */}
                {selectedJob.job_type === 'sicherstellung' && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <h4 className="font-semibold text-amber-800 mb-3">⚠️ Sicherstellung (Polizeilich)</h4>
                    <div className="grid sm:grid-cols-2 gap-3 text-sm">
                      <div>
                        <Label className="text-amber-700">Grund</Label>
                        <p className="font-medium">{
                          {
                            'betriebsmittel': 'Auslaufende Betriebsmittel',
                            'gestohlen': 'Gestohlenes Fahrzeug / Fahndung',
                            'eigentumssicherung': 'Eigentumssicherung (wertvoll/ungesichert)',
                            'technische_maengel': 'Technische Mängel / Beweissicherung',
                            'strafrechtlich': 'Strafrechtliche Beschlagnahme'
                          }[selectedJob.sicherstellung_reason] || selectedJob.sicherstellung_reason || '-'
                        }</p>
                      </div>
                      <div>
                        <Label className="text-amber-700">Fahrzeugkategorie</Label>
                        <p className="font-medium">{
                          selectedJob.vehicle_category === 'under_3_5t' ? 'PKW/Krad bis 3,5t' :
                          selectedJob.vehicle_category === 'over_3_5t' ? 'Fahrzeuge ab 3,5t' : '-'
                        }</p>
                      </div>
                      {selectedJob.ordering_authority && (
                        <div>
                          <Label className="text-amber-700">Anordnende Stelle</Label>
                          <p className="font-medium">{
                            {
                              'schutzpolizei': 'Schutzpolizei',
                              'kriminalpolizei': 'Kriminalpolizei',
                              'staatsanwaltschaft': 'Staatsanwaltschaft',
                              'sachverstaendiger': 'Technischer Sachverständiger'
                            }[selectedJob.ordering_authority] || selectedJob.ordering_authority
                          }</p>
                        </div>
                      )}
                      {selectedJob.contact_attempts !== null && (
                        <div>
                          <Label className="text-amber-700">Telefonische Kontaktversuche</Label>
                          <p className="font-medium">{selectedJob.contact_attempts ? 'Ja' : 'Nein'}</p>
                          {selectedJob.contact_attempts_notes && (
                            <p className="text-xs text-amber-600 mt-1">{selectedJob.contact_attempts_notes}</p>
                          )}
                        </div>
                      )}
                      {selectedJob.estimated_vehicle_value && (
                        <div>
                          <Label className="text-amber-700">Geschätzter Wert</Label>
                          <p className="font-medium">{selectedJob.estimated_vehicle_value.toLocaleString('de-DE')} €</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

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
                </div>

                {/* Timeline / Zeiterfassung */}
                <div className="bg-slate-50 rounded-lg p-4">
                  <Label className="text-slate-700 font-semibold mb-3 block flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Zeiterfassung
                  </Label>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.created_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">1. Meldung erfasst</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.on_site_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">2. Vor Ort angekommen</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.on_site_at ? new Date(selectedJob.on_site_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.towed_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">3. Abgeschleppt</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.towed_at ? new Date(selectedJob.towed_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.in_yard_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">4. Im Hof eingetroffen</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.in_yard_at ? new Date(selectedJob.in_yard_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.released_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">5. Fahrzeug abgeholt</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.released_at ? new Date(selectedJob.released_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
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
                      <div className="flex gap-2">
                        <Button
                          data-testid="status-towed-btn"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'towed')}
                          className="bg-red-500 hover:bg-red-600"
                        >
                          <Truck className="h-4 w-4 mr-2" />
                          Abgeschleppt
                        </Button>
                        <Button
                          data-testid="status-empty-trip-btn"
                          onClick={async () => {
                            try {
                              await axios.patch(`${API}/jobs/${selectedJob.id}`, { 
                                status: 'released',
                                is_empty_trip: true,
                                service_notes: 'Leerfahrt - Fahrzeug war nicht mehr vor Ort'
                              });
                              toast.success('Als Leerfahrt markiert');
                              fetchJobs();
                              setJobDetailOpen(false);
                            } catch (error) {
                              toast.error('Fehler beim Aktualisieren');
                            }
                          }}
                          variant="outline"
                          className="border-orange-500 text-orange-600 hover:bg-orange-50"
                        >
                          <X className="h-4 w-4 mr-2" />
                          Leerfahrt
                        </Button>
                      </div>
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
                        onClick={() => {
                          setReleaseDialogOpen(true);
                          fetchCalculatedCosts(selectedJob.id);
                        }}
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
        <DialogContent className="max-w-md">
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

            {/* Price Calculation Section */}
            <div className="space-y-3 p-4 bg-slate-50 rounded-lg border">
              <Label className="font-semibold">Kostenberechnung</Label>
              
              {/* Calculated Costs from Backend */}
              {loadingCosts ? (
                <div className="flex justify-center py-4">
                  <div className="loading-spinner"></div>
                </div>
              ) : calculatedCosts && calculatedCosts.breakdown?.length > 0 ? (
                <div className="text-sm text-slate-600 space-y-1">
                  {calculatedCosts.breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between">
                      <span>{item.label}:</span>
                      <span>{item.amount.toFixed(2)} €</span>
                    </div>
                  ))}
                  <div className="flex justify-between font-bold border-t pt-2 mt-2">
                    <span>Berechneter Gesamtpreis:</span>
                    <span className="text-green-600">{calculatedCosts.total.toFixed(2)} €</span>
                  </div>
                </div>
              ) : selectedJob?.in_yard_at ? (
                <div className="text-sm text-slate-600 space-y-1">
                  <div className="flex justify-between">
                    <span>Anfahrtskosten:</span>
                    <span>{(user?.tow_cost || 0).toFixed(2)} €</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Standtage:</span>
                    <span>{Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24)))} Tag(e)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Standkosten ({(user?.daily_cost || 0).toFixed(2)} €/Tag):</span>
                    <span>{(Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24))) * (user?.daily_cost || 0)).toFixed(2)} €</span>
                  </div>
                  <div className="flex justify-between font-bold border-t pt-2 mt-2">
                    <span>Berechneter Gesamtpreis:</span>
                    <span className="text-green-600">
                      {((user?.tow_cost || 0) + Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24))) * (user?.daily_cost || 0)).toFixed(2)} €
                    </span>
                  </div>
                </div>
              ) : null}
              
              <div className="flex gap-2 mt-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedJob?.in_yard_at) {
                      const days = Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24)));
                      const total = (user?.tow_cost || 0) + days * (user?.daily_cost || 0);
                      setPaymentAmount(total.toFixed(2));
                    }
                  }}
                  className="flex-1"
                >
                  <Euro className="h-4 w-4 mr-1" />
                  Berechnung übernehmen
                </Button>
              </div>

              <div className="space-y-2 mt-3">
                <Label htmlFor="paymentAmount" className="text-sm text-slate-500">Oder manuell eingeben:</Label>
                <Input
                  data-testid="release-amount-input"
                  id="paymentAmount"
                  type="number"
                  step="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  placeholder="Betrag eingeben..."
                  className="text-lg font-bold"
                  required
                />
              </div>
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

      {/* NEW: Create Job Dialog */}
      <Dialog open={createJobDialogOpen} onOpenChange={setCreateJobDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Car className="h-5 w-5 text-green-600" />
              Neuen Auftrag erstellen
            </DialogTitle>
            <DialogDescription>
              Erstellen Sie einen Auftrag für eine Behörde, mit der Sie verknüpft sind
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Authority Selection */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Behörde auswählen *</Label>
              {loadingAuthorities ? (
                <div className="flex items-center gap-2 text-slate-500">
                  <div className="loading-spinner h-4 w-4"></div>
                  Lade verknüpfte Behörden...
                </div>
              ) : linkedAuthorities.length === 0 ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800">
                  <p className="font-medium">Keine verknüpften Behörden</p>
                  <p className="text-sm mt-1">
                    Um Aufträge erstellen zu können, muss eine Behörde Sie zuerst über Ihren Verknüpfungscode hinzufügen.
                  </p>
                </div>
              ) : (
                <Select 
                  value={newJobData.for_authority_id} 
                  onValueChange={(value) => setNewJobData(prev => ({...prev, for_authority_id: value}))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Behörde auswählen..." />
                  </SelectTrigger>
                  <SelectContent>
                    {linkedAuthorities.map(auth => (
                      <SelectItem key={auth.id} value={auth.id}>
                        {auth.authority_name} ({auth.department || 'Keine Abteilung'})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Job Type */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Auftragsart</Label>
              <Select 
                value={newJobData.job_type} 
                onValueChange={(value) => setNewJobData(prev => ({...prev, job_type: value}))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="towing">Normaler Abschleppauftrag</SelectItem>
                  <SelectItem value="sicherstellung">Sicherstellung (Polizei)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Vehicle Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="newLicensePlate">Kennzeichen *</Label>
                <Input
                  id="newLicensePlate"
                  value={newJobData.license_plate}
                  onChange={(e) => setNewJobData(prev => ({...prev, license_plate: e.target.value.toUpperCase()}))}
                  placeholder="B-AB 1234"
                  className="uppercase"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="newVin">FIN (optional)</Label>
                <Input
                  id="newVin"
                  value={newJobData.vin}
                  onChange={(e) => setNewJobData(prev => ({...prev, vin: e.target.value.toUpperCase()}))}
                  placeholder="WDB1234567890"
                  className="uppercase"
                />
              </div>
            </div>

            {/* Tow Reason */}
            <div className="space-y-2">
              <Label htmlFor="newTowReason">Abschleppgrund *</Label>
              <Select 
                value={newJobData.tow_reason}
                onValueChange={(value) => setNewJobData(prev => ({...prev, tow_reason: value}))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Grund auswählen..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Falschparken">Falschparken</SelectItem>
                  <SelectItem value="Unfall">Unfall</SelectItem>
                  <SelectItem value="Panne">Panne</SelectItem>
                  <SelectItem value="Sicherstellung">Sicherstellung</SelectItem>
                  <SelectItem value="Polizeiliche Anordnung">Polizeiliche Anordnung</SelectItem>
                  <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Location */}
            <div className="space-y-2">
              <Label htmlFor="newLocationAddress">Standort/Adresse *</Label>
              <Input
                id="newLocationAddress"
                value={newJobData.location_address}
                onChange={(e) => setNewJobData(prev => ({...prev, location_address: e.target.value}))}
                placeholder="Musterstraße 1, 12345 Berlin"
              />
            </div>

            {/* Coordinates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="newLat">Breitengrad</Label>
                <Input
                  id="newLat"
                  type="number"
                  step="0.0001"
                  value={newJobData.location_lat}
                  onChange={(e) => setNewJobData(prev => ({...prev, location_lat: parseFloat(e.target.value) || 0}))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="newLng">Längengrad</Label>
                <Input
                  id="newLng"
                  type="number"
                  step="0.0001"
                  value={newJobData.location_lng}
                  onChange={(e) => setNewJobData(prev => ({...prev, location_lng: parseFloat(e.target.value) || 0}))}
                />
              </div>
            </div>

            {/* Sicherstellung Fields */}
            {newJobData.job_type === 'sicherstellung' && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg space-y-4">
                <h4 className="font-medium text-red-800">Sicherstellungs-Details</h4>
                
                <div className="space-y-2">
                  <Label>Sicherstellungsgrund</Label>
                  <Select 
                    value={newJobData.sicherstellung_reason}
                    onValueChange={(value) => setNewJobData(prev => ({...prev, sicherstellung_reason: value}))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Grund auswählen..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="stolen">Gestohlenes Fahrzeug</SelectItem>
                      <SelectItem value="evidence">Beweismittel</SelectItem>
                      <SelectItem value="danger">Gefahr im Verzug</SelectItem>
                      <SelectItem value="abandoned">Herrenlos / Verlassen</SelectItem>
                      <SelectItem value="court_order">Gerichtliche Anordnung</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Fahrzeugkategorie</Label>
                  <Select 
                    value={newJobData.vehicle_category}
                    onValueChange={(value) => setNewJobData(prev => ({...prev, vehicle_category: value}))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Kategorie auswählen..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="under_3_5t">Unter 3,5t</SelectItem>
                      <SelectItem value="over_3_5t">Über 3,5t</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Anordnende Stelle</Label>
                  <Select 
                    value={newJobData.ordering_authority}
                    onValueChange={(value) => setNewJobData(prev => ({...prev, ordering_authority: value}))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Stelle auswählen..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="police">Polizei</SelectItem>
                      <SelectItem value="prosecutor">Staatsanwaltschaft</SelectItem>
                      <SelectItem value="customs">Zoll</SelectItem>
                      <SelectItem value="court">Gericht</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="newVehicleValue">Geschätzter Fahrzeugwert (€)</Label>
                  <Input
                    id="newVehicleValue"
                    type="number"
                    value={newJobData.estimated_vehicle_value}
                    onChange={(e) => setNewJobData(prev => ({...prev, estimated_vehicle_value: e.target.value}))}
                    placeholder="z.B. 5000"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="newContactAttempts"
                      checked={newJobData.contact_attempts}
                      onChange={(e) => setNewJobData(prev => ({...prev, contact_attempts: e.target.checked}))}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="newContactAttempts">Kontaktversuche unternommen</Label>
                  </div>
                  {newJobData.contact_attempts && (
                    <Textarea
                      value={newJobData.contact_attempts_notes}
                      onChange={(e) => setNewJobData(prev => ({...prev, contact_attempts_notes: e.target.value}))}
                      placeholder="Details zu den Kontaktversuchen..."
                      rows={2}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="newNotes">Notizen</Label>
              <Textarea
                id="newNotes"
                value={newJobData.notes}
                onChange={(e) => setNewJobData(prev => ({...prev, notes: e.target.value}))}
                placeholder="Zusätzliche Informationen..."
                rows={3}
              />
            </div>

            {/* Photos */}
            <div className="space-y-2">
              <Label>Fotos</Label>
              <div className="flex flex-wrap gap-2">
                {newJobPhotos.map((photo, index) => (
                  <div key={index} className="relative">
                    <img 
                      src={photo} 
                      alt={`Foto ${index + 1}`} 
                      className="w-20 h-20 object-cover rounded border"
                    />
                    <button
                      type="button"
                      onClick={() => removeNewJobPhoto(index)}
                      className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => newJobFileInputRef.current?.click()}
                  className="w-20 h-20 border-2 border-dashed border-slate-300 rounded flex items-center justify-center hover:border-slate-400"
                >
                  <Camera className="h-6 w-6 text-slate-400" />
                </button>
                <input
                  type="file"
                  ref={newJobFileInputRef}
                  onChange={handleNewJobPhotoUpload}
                  accept="image/*"
                  multiple
                  className="hidden"
                />
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setCreateJobDialogOpen(false)}
                className="flex-1"
              >
                Abbrechen
              </Button>
              <Button
                onClick={handleCreateJob}
                disabled={creatingJob || linkedAuthorities.length === 0}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {creatingJob ? (
                  <>
                    <div className="loading-spinner h-4 w-4 mr-2"></div>
                    Erstelle...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Auftrag erstellen
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TowingDashboard;
